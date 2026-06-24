# EZ Metadata Extractor 
This app was create to easily export small to large amounts of meta-data contained within images. Specifically the ComfyUI Workflow metadata in .json format.



# If you are using the .exe file

Simply download and run the program, everything is self contained except for Exif Tool.

ExifTool found at https://exiftool.org/ 
This is needed to extract the meta-data from images, and videos.
Current version is 13.59 at the time of creating this repo.

Simply download Exif Tool and extract the program into a folder, then when asked to choose where exiftool is located in the app, choose the folder you extracted everything to.

# If you are using the .bat script

You will need Python v3.10 of greater installed.

Download the webp-metadata-extractor folder.
Download Exif Tool as mentioned above, use the .bat file inside the webp-metadata-extractor folder.
(In testing this didn't work reliably on other computers, which is why I made it a .exe  But to show the code of the program I included it anyway)

+Seed version of the .exe has a built in seed puller for convenience. 

Each seed is exported in its own .txt and is also the same name as the input image/video.


# How to use the program

From the main EZ Metadata Extractor window, at the top there is a section called ExifToll Location. Choose the folder where you extracted ExifTool at.

Next choose the type of image you wish to process. PNG, WebP, Mp3, and Mp4 can all be processed using this app. Select whether you want a single file or every file in a folder that matches the extension selected.

Next choose the folder you wish all the meta-data files to be exported too. You can choose from various formats like ComfyUI Workflow .json, .mb (markdown), .txt (plaintext), .html (for the lols), and basic .json.

Recommended to perform a dry run before processing as to ensure you have everything ready for processing.
Upon complete a **dry run**, you will be given a summary of what will be processed.

Large folders will take some time to process depending on the amount of meta-data inside each image and how many total images there are. Testing was done on a batch of 200 images and processing time was about 20 seconds.

Once you are satisfied with everything, click **Process** and wait for it finish. Inside the output folder you have selected previously will be all of the metadata neatly extracted and also in the same name as the original file as to not cause confusion later on.
