# Alter or Create a new spreadsheet form

## Alter or create?

All Spreadsheet forms have old versions kept when backwards incompatible changes are made.

If the change you are making is only superficial, such as changing a label, some text or a styling, you can just alter the current form.

If the change you are making changes the data that can be put into or extracted from the form in any way, make a new version.

## Alter a spreadsheet form

Open the latest version of the spreadsheet form.

Alter at will.

Excel files save the current position of the cursor and tabs. In order to make sure the person opening the spreadsheet gets a good experience, go to every tab and make sure the cursor is in cell A1. Then make sure the first tab is selected. Then save the spreadsheet for the final time and close it.

[Rebuild the caches checked into git](rebuild-caches-checked-in-to-git.md)

Use `git diff` to check for any changes in the caches. If there are any, that probably indicates that the changes you are making are not superficial and you should instead be making a new version.

Test your changes!

Commit your changes and make a pull request.

## Create a new spreadsheet form

If you are doing this, you probably need to update the schema in https://github.com/INDIGO-Initiative/indigo-data-standard/tree/main/schema . Do this on a new branch. Then update the submodule in `data-standard` to point to the new branch. 

Open the latest version of the spreadsheet form. Save it as the new version.

On the first tab, there may be a cell with a special marker that specifies what version it is. Update this.

Alter at will.

Excel files save the current position of the cursor and tabs. In order to make sure the person opening the spreadsheet gets a good experience, go to every tab and make sure the cursor is in cell A1. Then make sure the first tab is selected. Then save the spreadsheet for the final time and close it.

[Rebuild the caches checked into git](rebuild-caches-checked-in-to-git.md)

Tell the app about your new version. Look in `djangoproject/settings.py` for the `JSONDATAFERRET_TYPE_INFORMATION` variable. 

If changing a public spreadsheet: Change the `spreadsheet_public_form_guide` variable. You also should search the code for any instances of the old name and manually change it to the new name, as not all code has been updated to use these settings yet.

If changing a non-public spreadsheet: Change `spreadsheet_form_guide` and `spreadsheet_form_guide_spec`. Add a new row to `spreadsheet_form_guide_spec_versions`.

Make any other changes you need to the app. For instance, you may have to update some keys in `indigo/__init__.py`.

Test your changes!

Once you are happy and the client has signed off (if necessary) you may need to merge your schema changes to the main branch in `https://github.com/INDIGO-Initiative/indigo-data-standard`. Then update the submodule here, and send the pull request off for review!
