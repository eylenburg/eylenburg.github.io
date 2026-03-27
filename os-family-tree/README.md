This is the raw data used to create the [family tree of operating systems](https://eylenburg.github.io/os_familytree.htm), which is rendered using gnuclad.

Some of the dates are estimates based on e.g. the years of the project website going online and being taken down. 

If anyone can contribute corrections that will be much appreciated.

Please note that some operating systems have their end date set to the year 2100 to avoid running into a bug in gnuclad.

## Contribution guide
The ````.SVG```` file is generated from the ````.CSV```` file using the ````gnuclad```` tool.

### Installation
gnuclad can be installed via flatpack or snap.

Snap:
````
sudo snap install gnuclad
````

Flatpak:
````
flatpak install flathub net.launchpad.Gnuclad
````

You can also use the [official Debian binary](https://launchpad.net/gnuclad/+download).

### How to edit the .CSV file

The CSV file can be edited with LibreOffice Calc, for example. It is important here that all lines are formatted as text when opening the CSV file in order to prevent, for example, a date from being automatically adjusted. If you open in in Microsoft Excel, make sure to save it as "CSV (Comma delimited") (note there are multiple variants of the CSV format in Excel, you must use this one).

The columns in the CSV file are as follows:

- what the row is about e.g. "N" for a node , or "#" for a comment
- Name of the OS, this has to be the name of the first release if the OS was renamed later
- Color; here please follow the current scheme (Dark Purple: Apple, Cyan: Microsoft, Red: Unix-like, Green: RSX/VMS-like, Dark Blue: DOS-like, Orange: AmigaOS-like, Brown: mainframe systems, Yellow: L4 microkernel family, Bright Purple: OSEK-compliant), note that for Unix there are two colours depending on whether the OS is still alive or not
- Parent: for forks of another OS, this has to EXACTLY match the name of the parent OS
- Start: first release date. Dates always have to be in the format YYYY.MM.DD (days and months are optional)
- Stop: end of support date for discontinued OS, leave blank otherwise. One issue here is that you cannot have a fork starting after the parent OS is already dead.
- Icon: ignore
- Description: ignore
- Namechange: if the OS was renamed, enter the new name here
- When: date of the name change
- Description: ignore
- then a couple more columns (Namechange, When, Description) for additional name changes

What counts as a fork? 
Anything that is based on the code of the previous OS. If it's just a commercial successor but on a completely technical basis (such as BlackBerry OS 7 -> BlackBerry 10) this needs to be a completely separate branch. 

What counts as an OS?
Anything that can run on bare metal. It doesn't need to be fancy; a tiny embedded OS can still count. Please don't add every Linux distro or Windows variant, it's out of scope.



### How to create the .SVG file

Once the changes have been made to the CSV file, the SVG file can be generated with the following command:
````
gnuclad file.csv output.svg config.conf
````

or for the Flatpak:
````
flatpak run net.launchpad.Gnuclad file.csv output.svg config.conf
````

Example:
````
gnuclad Eylenburg_Operating_System_Timeline_Family_Tree.csv Eylenburg_Operating_System_Timeline_Family_Tree.svg Eylenburg_Operating_System_Timeline_Family_Tree.conf
````

````
flatpak run net.launchpad.Gnuclad Eylenburg_Operating_System_Timeline_Family_Tree.csv Eylenburg_Operating_System_Timeline_Family_Tree.svg Eylenburg_Operating_System_Timeline_Family_Tree.conf
````

### Bugs in Gnuclad

Sometimes a bug occurs when you try to create the SVG: "X starts after its parent ends". In this case just add the year 2100 to the parent's end date.

Sometimes a different bug occurs when you try to create the SVG "Error: X starts before it's parent". This is because another node (completely unrelated) has an empty name, probably on purpose. Replacing that empty cell with a space character will fix the error.

### Add viewBox attribute for embedding in websites

At the end, edit the SVG in a text editor, and in the `<svg>` tag at the beginning, just below where it says something like `width='2270'` and `height='38240'` but before the closing bracket `>`, add a new line saying `viewBox='0 0 2270 38240'`. Make sure the capitalization of `viewBox` is correct and that the width and height are the same numbers as in the lines above. This is needed for embedding the SVG in the website.
