# SwamPy
<img width="256" height="256" alt="256" src="https://github.com/user-attachments/assets/590d74b2-c476-48f5-ae57-ee5cbcc21705" />
<h3>Poor quality frontend for CrocDB</h3>
This program is shoddy but at least you can start it up from ES-DE. 

It has an option to extract the games according to Emulation Station's folder mapping.

It's not the worst thing ever, provided you don't look at the source code.

If you think of a good feature to add (e.g. bite the bullet and use chdman for converting the 1% of ROMs only available as bin/cue) or get annoyed by a bug or behaviour, feel free to open up an issue.

<img width="1366" height="768" alt="image" src="https://github.com/user-attachments/assets/cd985785-4feb-4fed-93a5-cff048786cd9" />

Move the focus around with arrow keys, go back and forth through pages with PgUp/Dn.
Filters demos out and moves extracted multi-disc CHDs to .m3u folders by default.
If you want to use pyinstaller on it yourself, I'd recommend using the b64 version so you don't need the images.

Features to add: 
* Queue management beyond cancelling and clearing
    * I'm sure there's a way to download faster, not sure exactly how though.
* Filter by filesize, maximum and minimum
* Identify and display missing discs in multi-disc series
* Identify duplicates
* Export/Import romsets as a list of slug identifiers
* Make use of the /entry/random endpoint somehow. Probably on startup if the user doesn't have/want missing/duplicate ROMs to be displayed.

