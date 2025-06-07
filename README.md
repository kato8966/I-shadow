# I-shadow

Improve your English while enjoying shadowing!

## Supported Platform

- Linux on x86_64
- Linux on arm64
- OSX (both x86 and M1)
- Windows x86 and 64

## Requirements

- Python 3.12.3 or higher

### Additional Requirements for Linux Users

- PortAudio
- libasound2-plugins

## How to Use (with a YouTube Video)

1. Click the green "Code" button and select "Download ZIP"
2. Unzip the downloaded file
3. Move to the unzipped directory
4. Create a virtual environment and install the required Python packages in it (`pip install -r requirements.txt`)
5. Run [i-shadow.py](i-shadow.py)
6. Go to [YouTube](https://www.youtube.com) and find a video you want to shadow
7. Open the video and pause it at the beginning
8. Open the description of the video and click "Show transcript"
9. In the transcript pane, click the three-dotted menu and select "Toggle timestamps" to hide timestamps
10. Copy the transcript and paste it into the text box of the I-shadow app (But try not to see the transcript while shadowing!)
11. Click the mic button and start playing the video
12. Shadow the video by repeating what you hear
13. Click the mic button again to stop recording
14. Check your shadowing scores (Read the section below for details on the scores)
15. You can post the result to X by clicking the "Post result to X" button
    - Don't forget to replace `***` with the URL of the video

## How to Interpret the Scores

Precision is the percentage of correctly shadowed words out of the total words you spoke.
Recall is the percentage of correctly shadowed words out of the total words in the transcript.
The F1 score is the harmonic mean of precision and recall.

For example, let's say you shadowed an audio clip saying "Hello, world! Happy coding!"
If you spoke "Hello. Coding." your precision would be 100% (2 out of 2 words you spoke were correct).
However, the recall would be 50% (2 out of 4 words in the transcript were correctly shadowed), resulting in an F1 score of 67%.

Try to maximize both precision and recall to achieve a high F1 score!
