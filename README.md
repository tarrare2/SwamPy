# SwamPy
<img width="256" height="256" alt="256" src="https://github.com/user-attachments/assets/590d74b2-c476-48f5-ae57-ee5cbcc21705" />
<h3>Poor quality frontend for CrocDB</h3>
This program is shoddy but at least you can start it up from ES-DE. 

It has an option to extract the games according to Emulation Station's folder mapping.

It's not the worst thing ever, provided you don't look at the source code.

If you think of a good feature to add (e.g. bite the bullet and use chdman for converting the 1% of ROMs only available as bin/cue) or get annoyed by a bug or behaviour, feel free to open up an issue.

<img width="1366" height="768" alt="Something to note: the second 'nes'/third label is the file format of the download link, not the platform." src="https://github.com/user-attachments/assets/3c317a3c-3f25-45cb-a694-06c11578daea" />


### Instructions:
1. Put the script/executable in a folder you don't mind having a config in.
   * If you're using the script, pip install the modules in requirements.txt
2. Select platforms and regions, if any. Type keywords in the search bar, if any. Press enter or click the Search button.
3. If there are results, the cover art will be shown if it's available, otherwise the croc will be shown.
   * Below every card is the title of the game, along with the platform | region | file format
4. Move the focus around with arrow keys, go back and forth through pages with PgUp/Dn. Pressing enter with a game in focus will download it.
   * CHDs and other single file formats take precedence over bin/cue and other obsolete formats.
5. Filters demos out and moves extracted multi-disc CHDs to .m3u folders by default. This can be changed in the settings.
   * If you're using ES-DE, change the download folder in the settings to ES-DE/ROMs and don't turn off the folder mapping switch.
   * The .m3u switch will prevent Emulation Station from counting multiple discs as separate games for a few specific platforms.
   * Also remember to move the script/executable or a shortcut to it in ES-DE/ROMs/emulators for convenience.
6. Extracts ROMs automatically but only if they only contain a single item (this is for emulators that are compatible with zips with a large number of tracks). Otherwise, they must be extracted manually.
Optional: Turn off automatic .m3u folders and folder mapping if you prefer to have all the ROMs in the same top level folder

If you want to use pyinstaller on it yourself, I'd recommend using the b64 version so you don't need the images.

### Features to add: 
* Queue management beyond cancelling and clearing e.g. pause/resume/priority
    * I'm sure there's a way to download faster, not sure exactly how though.
* Filter by filesize, maximum and minimum
* Detect and display missing discs in multi-disc series
* Detect and display duplicates
* Export/Import romsets as a list of slug identifiers
  * Beg crocDB to expose the website's romsets to the API as a TSV or txt.
* Make use of the /entry/random endpoint somehow. Probably on startup if the user doesn't have/want missing/duplicate ROMs to be displayed.

