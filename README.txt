In case you make changes to the code and need to rebuild the executable, follow these steps:

**Notes**:
- Three main scripts are used to generate this application: `parcel_main.py`, `planner.py`, and `parcel_gen.py`.
- Translation is available only for Spanish, and the translation file used in the executable is named `translated_es.qm`.
- Additional files or folders may be specified in the `parcel_main.spec` file.
- The `parcel_main.spec` file is used to generate the executable.

**Steps**:

0. Activate the virtual environment by running `env/Scripts/activate` to use the environment’s Python.

1. Make any desired changes to the code.

2. Add `self.tr()` around any new strings that should be translated.

3. To update the `.ts` file, run: pylupdate6 parcel_main.py planner.py -ts translated_es.ts

4. To automatically generate translations, run the script located at `C:\Users\Getac\Documents\Omer Mersin\codes\tools\main.py`.

5. Review the `.ts` file for common mistakes/typos, especially for terms like "m," "y," "x," "GAP," "Open," "English," "Español," and "white." Correct any errors before generating the `.qm` file.

6. Open the `.ts` file in Qt Linguist, make final adjustments if needed, then save and release it as a `.qm` file.

7. Place the generated `.qm` file in the same directory as `parcel_main.spec`.

8. To generate the executable, run: pyinstaller parcel_main.spec
