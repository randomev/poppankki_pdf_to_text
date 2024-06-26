# Finnish POP Bank PDF parser

## This program
- Reads Finnish POP-Bank ("POP-PANKKI") PDF-statements
- Converts those pdf-files to a text representation on the fly
- Tries to parse transactions best it can
- Manipulates target names and groups by provided configuration parameters
  - regexp_target_modifications (you can modify with regexp names, such as "ELECTRICITY" from .*fortum.* and .*elec.* etc.)
  - third_line_text_to_target (sometimes descriptive part of transaction is on the third line of parsed text, this can be filled then)
  - top_level_groupings (this can be used to group by names of senders and receivers of money)
  - items_to_remove (such as your own internal bank account transfers eg. from account 1 to account 2. This is just putting money from another pocket to another pocket and in some sense it's not interesting. If this applies to you,
  you can remove these transactions here by providing sender or receiver names or accounts here. )
- Sorts results based on amount of money
- Outputs to selected format (for now, only prettified text)

* Aim is to produce quick glance without any extra Excel effort since Excel is manual labor and prone to lazyness of updating. Instead just download a new bank PDF-statement and see where has the money gone this time.

* Create yearly config files to easily run yearly stats whenever needed

* Create a config file that takes a parent directory of your years and see total grouping of all time where the money has gone. (So that config file would point to "/pdf" directory)

* Not pay extra banking fees of 2 eur / csv export of 1000 lines - this is way too steep price for such a thing

## How to use

1) Get your account monthly report pdf-files from your POP Bank web-app (for 1 year you need 12 pdf-files in total)
2) Save them to a yearly folder, say pdf/2023
3) Copy config-sample.json to config2023.json modify pdf_dir to point to that yearly folder
4) run "python3 lue_pop-pankki_pdf_tiliotteet.py config2023.json"
5) there should be pdf/2023/output_pretty.txt that looks something like this

```
--------------------
SAVING AND INVESTEMENTS: -1200.0 (per month: -100)
  * EXTRA PAYMENTS: -50.0
  * NORDNET: -50.0
--------------------
FOOD TOTAL: -6000.0 (per month: -500.0)
  * FOODSTORE A: -3000.0
  * FOODSTORE B: -3000.0
--------------------
--------------------
MORTAGE PAYMENTS TOTAL: -12000.0 (per month: -1000.0)
  * MORTAGE PAYMENTS: -12000.0 (per month: -1000.0)
--------------------
````

Repeat 1-5 for other years and compare. One folder and config-file for each year. And then one config file to point to parent folder of all years to see all years together.


You can also share some part of config between years by using "include" such as

config2024.json:
```
{
    "months": 3,
    "pdf_dir": "/Users/a/pdf/2024",
    "output_dir": "/Users/a/pdf/2024",
    "output_format": "pretty",
    "include": "/Users/a/pdf/common_config.json"
}
```
and then common_config.json could for example contain groupings and modification shared between years:

```
{
    "items_to_remove": 
        [
            "SOMETHING I DONT WANT"
        ],
    "top_level_groupings": {
        "MORTAGE PAYMENTS": ["MORTAGE"],
        "SAVING AND INVESTEMENTS": ["NORDNET", "EXTRA PAYMENTS"],
        "APOTECS": [
            "APOTEC",
            "APT"
            ],
        "FOOD": [
            "FOODSTORE A",
            "FOODSTORE B"
            ]
    },

    "regexp_target_modifications": 
    {
        "ELECTRICITY": [".*fortum.*"],
        "ELECTRICITY GRID COMPANY": [".*caruna.*"]
    }
}
```
This way you can use same definitions for each year and definition grows over time when you input more and more groupings. You can always run older years with newer groupings to get 1:1 comparison with a new groups you have defined. 