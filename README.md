# EZ Metadata Extractor 
This app was create to easily export small to large amounts of meta-data contained within images. Specifically the ComfyUI Workflow metadata in .json format.

To run this app, you will need Python 3.10 or greater. As well as ExifTool found at https://exiftool.org/
Current version is 13.59 at the time of creating this repo.

Download and extract Exif Tool onto your computer and then run the Run-Webp-Metadata-Extractor.bat file. 

Download and open the .exe file.
Or use the .bat file inside the webp-metadata-extractor folder.

From the main EZ Metadata Extractor window, at the top there is a section called ExifToll Location. Choose the folder where you extracted ExifTool at.

Next choose the type of image you wish to process. PNG, WebP, Mp3, and Mp4 can all be processed using this app. Select whether you want a single file or every file in a folder that matches the extension selected.

Next choose the folder you wish all the meta-data files to be exported too. You can choose from various formats like ComfyUI Workflow .json, .mb (markdown), .txt (plaintext), .html (for the lols), and basic .json.

Recommended to perform a dry run before processing as to ensure you have everything ready for processing.
Upon complete a **dry run**, you will be given a summary of what will be processed.

Large folders will take some time to process depending on the amount of meta-data inside each image and how many total images there are. Testing was done on a batch of 200 images and processing time was about 20 seconds.

Once you are satisfied with everything, click **Process** and wait for it finish. Inside the output folder you have selected previously will be all of the metadata neatly extracted and also in the same name as the original file as to not cause confusion later on.
