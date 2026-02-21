# SwamPy
<img width="256" height="256" alt="256" src="https://github.com/user-attachments/assets/590d74b2-c476-48f5-ae57-ee5cbcc21705" />
<h3>Poor quality frontend for CrocDB</h3>
This program is shoddy but at least you can start it up from ES-DE. 

It has an option to extract the games according to Emulation Station's folder mapping as well as run the crocAPI server locally
* (If you're not using the executable, you need the roms.db file. It's 200MB+ so I won't upload it here. It can be acquired with this: https://github.com/cavv-dev/crocdb-db)

It's not the worst thing ever, provided you don't look at the source code.

If you think of a good feature to add that isn't already written below (e.g. bite the bullet and use chdman for converting the 1% of ROMs only available as bin/cue) or get annoyed by a bug or behaviour, feel free to open up an issue.

<img width="1366" height="768" alt="Something to note: the second 'nes'/third label is the file format of the download link, not the platform." src="https://github.com/user-attachments/assets/3c317a3c-3f25-45cb-a694-06c11578daea" />


### Instructions:
1. Put the script/executable in a chosen folder then run it.
   * If you're using the script, pip install the modules in requirements.txt (and if you want to use the local API put the crocAPI in a folder called 'mangrove', inside the mangrove folder put the roms.db file in a folder called 'db'.)
2. If you want to use the local server, open up the settings and click configure. Once you've chosen the host and port, start the server. You can also choose to start it automatically next time.
3. Select platforms and regions, if any. Type keywords in the search bar, if any. Press enter or click the Search button.
4. If there are results, the cover art will be shown if it's available, otherwise the Croc will be shown.
   * Below every card is the title of the game, along with the platform | region | file format
5. Move the focus around with arrow keys, go back and forth through pages with PgUp/Dn. Pressing enter with a game in focus will download it.
   * CHDs and other single file formats take precedence over bin/cue and other obsolete formats.
6. It filters demos out and moves extracted multi-disc CHDs to .m3u folders by default. This can be changed in the settings.
   * If you're using ES-DE, change the download folder in the settings to ES-DE/ROMs and don't turn off the folder mapping switch.
   * The .m3u switch will prevent Emulation Station from counting multiple discs as separate games for a few specific platforms.
   * Also remember to move the script/executable or a shortcut to it in ES-DE/ROMs/emulators for convenience.
7. Extracts ROMs automatically but only if they only contain a single item (this is for emulators that are compatible with zips with a large number of tracks). Otherwise, they must be extracted manually.
   * If you're using Vita3K and ES-DE, make sure to set the path to Vita3K in the settings to automatically install PKGs and also make a .psvita file in ROMs/psvita so you can start the game from ES-DE.
Optional: Turn off automatic .m3u folders and folder mapping if you prefer to have all the ROMs in the same top level folder

The images are base64 strings. I know it's not a good decision but I find it's more convenient than having a folder for images.

### Features to add upon request or spontaneous motivation: 
* If using ES-DE: hopefully it's possible to autoscrape metadata for downloaded titles from screenscraper.fr into ES-DE/downloaded_media
* Queue management beyond cancelling and clearing e.g. proper pause/resume/priority/parallel
    * I'm sure there's a way to download faster, not sure exactly how though.
* Download speed limiting
* Filter by filesize, maximum and minimum
* Use cachetools to make it faster
* Detect and display missing discs in multi-disc series
* Detect and display duplicates
* Make use of the /entry/random endpoint somehow. Probably on startup if the user doesn't have/want missing/duplicate ROMs to be displayed.
* ~~Export/Import romsets as a list of slug identifiers~~
  * Beg crocDB to expose the website's romsets to the API as a TSV or txt.
  * Alternatively man up and do it myself (although compared to a central hub for everyone to use, adding an API endpoint for your text files just isn't the same)
* ~~PSVita games don't have covers or zRIFs (they were put on crocdb.net), so~~ do the following:
    1. ~~Add covers to PSV games using my psv-covers repo~~
    2. ~~Download nopaystation's TSV, extract zRIFs~~
    3. ~~Use zRIF, if present, to decrypt the downloaded PKG files into .zips~~
    4. ~~(Optional) Install .pkg+zRIF or .zip using Vita3K's CLI to automatically install a package~~
      * pkg+zRIF is chosen over zip otherwise Vita3K will run the game.
    5. ~~If ES-DE folders are being used, create .psvita files in place of the .pkg files for ES-DE to display and run.~~
    6. Show/Filter by Vita3K's compatibility list (WIP)
* ~~Option to run the API server locally~~

