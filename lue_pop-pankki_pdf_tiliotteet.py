import PyPDF2
import re
import pprint
from collections import defaultdict
import os
import csv
import json
import argparse


def load_config(config_path):
    with open(config_path) as f:
        config = json.load(f)
    return config

def parse_transactions(text, filename, config):
    transactions = []
    transaction = []
    end_strings = ['ARN:', 'SUOMAKSU', 'E-LASKU']
    lines = text.split('\n')
    header_ended = False
    transaction_open = False
    for line in lines:
        if line.startswith('TILIOTE'):
            header_ended = False
            transaction_open = False
        if re.match(r'\s{10,}SIIRTO', line) or re.match(r'\s{10,}SALDO', line):
            if transaction and header_ended:
                transactions.append('\n'.join(transaction))
            transaction = []
            transaction_open = False
        if re.match(r'\d{2}\.\d{2} \d{2}\.\d{2}', line):
            if transaction and header_ended:
                transactions.append('\n'.join(transaction))
            transaction = []
            transaction.append(line)
            header_ended = True
            transaction_open = True
        elif any(line.strip().startswith(end_string) for end_string in end_strings):
            transaction.append(line)
            transactions.append('\n'.join(transaction))
            transaction = []
            transaction_open = False
        elif line.strip() == '':
            if transaction and header_ended:
                transactions.append('\n'.join(transaction))
            transaction = []
            transaction_open = False            
        elif transaction_open:
            transaction.append(line)
    #if transaction and header_ended:
    #    transactions.append('\n'.join(transaction))
    return transactions

def parse_amounts_and_lines(transactions, config):
    third_line_text_to_target = config['third_line_text_to_target']

    parsed_transactions = []
    for transaction in transactions:
        lines = transaction.split('\n')
        dates = re.findall(r'\d{2}\.\d{2}', lines[0])
        kirjauspvm = dates[0] if dates else None
        arvopvm = dates[1] if len(dates) > 1 else None
        target = re.sub(r'\s*/[AJ]', '', lines[0][11:].strip()) if len(lines[0]) > 11 else None
        if target != None:
            target = target.upper()

        second_line = lines[1] if len(lines) > 1 else None
         
        if len(lines) > 2:
            third_line = lines[2]

            for common_name, names in third_line_text_to_target.items():
                #print("third_line: " + third_line)
                if any(re.match(name, third_line, re.IGNORECASE) for name in names):
                    target = common_name
        else: 
            third_line = None

        reversed_last_line = lines[-1][::-1]
        match = re.search(r'(\d{2},\d+(\s*\d+)*[-+])', reversed_last_line)

        if match:
            amount = match.group()[::-1].replace(" ", "").strip()
        else:
            amount = None
            print("PROBLEM WITH AMOUNT:")
            print(transaction)
        
        parsed_transactions.append({
            'kirjauspvm': kirjauspvm,
            'arvopvm': arvopvm,
            'target': target,
            'amount': amount,
            'rivi2': second_line,
            'rivi3': third_line,
        })
    return parsed_transactions

def sum_amounts_by_target(parsed_transactions, config):
    sums = defaultdict(lambda: defaultdict(float))

    regexp_target_modifications = config['regexp_target_modifications']
    top_level_groupings = config['top_level_groupings']

    for transaction in parsed_transactions:
        if transaction['amount']:
            # Replace comma with dot for float conversion
            amount = float(transaction['amount'].replace(',', '.'))
            target = transaction['target']
            common_name = None
            for common_name, names in regexp_target_modifications.items():
                if any(re.match(name, target, re.IGNORECASE) for name in names):
                    target = common_name
                    break
            for top_level_name, common_names in top_level_groupings.items():
                if any(name in target for name in common_names) or top_level_name in target: 
                    sums[top_level_name][target] += amount
                    sums[top_level_name]['total'] += amount

                    break
            else:
                sums[target]['total'] += amount
    return sums

def main():
    master_parsed_transactions = []

    pp = pprint.PrettyPrinter(indent=4)

    # Create the parser
    parser = argparse.ArgumentParser(description='Process some integers.')

    # Add the arguments
    parser.add_argument('ConfigPath', metavar='ConfigPath', type=str, help='the path to the config file')

    # Parse the arguments
    args = parser.parse_args()

    config = load_config(args.ConfigPath)

    pdfdirectory = config['pdf_dir']
    output_dir = config['output_dir']
    print("pdfdirectory: " + pdfdirectory)
    print("output_dir: " + output_dir)

    for root, dirs, files in os.walk(pdfdirectory):
        for filename in files:
            #print("Processing file: " + filename)
            if filename.endswith(".pdf"):
                name=os.path.join(root, filename)
                #print("Processing file: " + name)
                with open(name, "rb") as pdf_file:
                    #with open("sample.pdf", "rb") as pdf_file:
                    read_pdf = PyPDF2.PdfReader(pdf_file)
                    #number_of_pages = read_pdf.getNumPages()

                    for page in read_pdf.pages:

                #    page = read_pdf.pages[0]
                        page_content = page.extract_text()
                        #print(page_content)
                        transactions = parse_transactions(page_content, name, config)
                        #pp.pprint(transactions)

                        parsed_transactions = parse_amounts_and_lines(transactions, config)
                        master_parsed_transactions.extend(parsed_transactions)

    # Sort transactions alphabetically by target
    master_parsed_transactions.sort(key=lambda x: x['target'])

    filename = 'transactions_backup.csv'
    full_path = os.path.join(output_dir, filename)

    # Save transactions to a CSV file for cross-checking them to our result
    with open(full_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Target', 'Amount', 'Kirjauspvm', 'Arvopvm', 'Rivi2', 'Rivi3'])

        for transaction in master_parsed_transactions:
            writer.writerow([transaction['target'], transaction['amount'], transaction['kirjauspvm'], transaction['arvopvm'], transaction['rivi2'], transaction['rivi3']])
            #if transaction['amount'] == None:
            #    pp.pprint(transaction)

    sums = sum_amounts_by_target(master_parsed_transactions,config)

    # Remove the items that are marked to be removed
    items_to_remove = config['items_to_remove']

    # Remove the items from sums
    for item in items_to_remove:
        if item in sums:
            del sums[item]

    output_format = config['output_format']

    if output_format == 'pretty':
        filename = 'output_pretty.txt'
        full_path = os.path.join(output_dir, filename)

        # Save transactions to a CSV file for cross-checking them to our result
        with open(full_path, 'w') as f:

            # Text output
            for target, sub_sums in sorted(sums.items(), key=lambda item: item[1]['total'], reverse=True):
                total = round(sub_sums['total'], 2)
                if len(sub_sums) == 1 and 'total' in sub_sums:
                    if total < -5000:
                        print(f"{target}: {total} (per kk: {round(total/12, 0)})", file=f)
                    else:
                        print(f"{target}: {total}", file=f)
                else:
                    print("--------------------", file=f)
                    print(f"{target} YHTEENSÄ: {total} (per kk: {round(total/12, 0)})", file=f)
                    for sub_target, sum in sorted(sub_sums.items(), key=lambda item: item[1], reverse=False):#sorted(sub_sums.items()):
                        if sub_target != 'total':
                            if sum < -5000:
                                print(f"  * {sub_target}: {round(sum,2)} (per kk: {round(sum/12, 0)})", file=f)
                            else:
                                print(f"  * {sub_target}: {round(sum,2)}", file=f)
                    print("--------------------", file=f)


    if output_format == 'html_tree':
        html = """
        <html>
        <head>
        <link rel="stylesheet" type="text/css" href="style.css">

        </head>
        <body>
        <div class="tree">
        <ul>
        """

        for target, sub_sums in sorted(sums.items(), key=lambda item: item[1]['total'], reverse=True):
            total = round(sub_sums['total'], 2)
            html += f"<li><span onclick='toggleVisibility(this)'>{target}: {total}</span>"
            if len(sub_sums) > 1:
                html += "<ul style='display: none'>"
                for sub_target, sum in sorted(sub_sums.items(), key=lambda item: item[1], reverse=False):
                    if sub_target != 'total':
                        html += f"<li>{sub_target}: {round(sum,2)}</li>"
                html += "</ul>"
            html += "</li>"

        html += "</ul></div>"

        html += """
        <script>
        function toggleVisibility(element) {
            var childList = element.parentNode.querySelector("ul");
            if (childList.style.display === "none") {
                childList.style.display = "block";
            } else {
                childList.style.display = "none";
            }
        }
        </script>
        </body></html>
        """

        # Write the HTML to a file
        with open("output.html", "w") as file:
            file.write(html)


if __name__ == "__main__":
    main()