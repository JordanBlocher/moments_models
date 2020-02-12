import functools
import os
import re
import subprocess

import numpy as np
from PIL import Image

import cv2

from tempfile import mkdtemp

def extract_audio(video_name, num_frames=8):

    print('mplayer -ao pcm:fast:file="audiofile.wav" -vo null -vc null "' + video_name + '"')
    audio = subprocess.Popen(['mplayer', '-ao',
    'pcm:fast:file="audiofile.wav"','-vo', 'null', '-vc', 'null', video_name], stderr=subprocess.PIPE).communicate()

def extract_frames(video_file, num_frames=8):
    """Return a list of PIL image frames uniformly sampled from an mp4 video."""
    try:
        os.makedirs(os.path.join(os.getcwd(), 'frames'))
    except OSError:
        pass
    output = subprocess.Popen(['ffmpeg', '-i', video_file],
                              stderr=subprocess.PIPE).communicate()
    # Search and parse 'Duration: 00:05:24.13,' from ffmpeg stderr.
    re_duration = re.compile(r'Duration: (.*?)\.')
    duration = re_duration.search(str(output[1])).groups()[0]

    seconds = functools.reduce(lambda x, y: x * 60 + y,
                               map(int, duration.split(':')))
    rate = num_frames / float(seconds)

    output = subprocess.Popen(['ffmpeg', '-i', video_file,
                               '-vf', 'fps={}'.format(rate),
                               '-vframes', str(num_frames),
                               '-loglevel', 'panic',
                               'frames/%d.jpg']).communicate()
    frame_paths = sorted([os.path.join('frames', frame)
                          for frame in os.listdir('frames')])
    frames = load_frames(frame_paths, num_frames=num_frames)
    subprocess.call(['rm', '-rf', 'frames'])
    return frames


def load_frames(frame_paths, num_frames=8):
    """Load PIL images from a list of file paths."""
    frames = [Image.open(frame).convert('RGB') for frame in frame_paths]
    if len(frames) >= num_frames:
        return frames[::int(np.ceil(len(frames) / float(num_frames)))]
    else:
        raise ValueError('Video must have at least {} frames'.format(num_frames))


def render_frames(frames, prediction):
    """Write the predicted category in the top-left corner of each frame."""
    rendered_frames = []
    tmp_dir = mkdtemp()
    i = 0
    for frame in frames:
        img = np.array(frame)
        height, width, stride = img.shape
        cv2.putText(img, prediction,
                    (1, int(height / 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 255, 255), 2)
        rendered_frames.append(img)
        rimg =  Image.fromarray(img, "RGB")
        rimg.save(tmp_dir + "/screen%04d.png" % i)
        i += 1
    
    return tmp_dir

def render_video(tmp_dir, video_name, num_frames=8):

    fps = 25
    audio_file = extract_audio(video_name, num_frames)
    print('mencoder mf:'+str(tmp_dir)+'/*.png -mf fps='+str(fps)+ ' -audiofile audiofile.wav -oac lavc -ovc lavc -lavcopts vcodec=mpeg4:vbitrate=800 -o prediction.avi')
    video = subprocess.Popen(['mencoder', 'mf://'+str(tmp_dir)+'/*.png', '-mf',
    'fps='+str(fps), '-audiofile', 'audiofile.wav', '-oac', 'lavc', '-ovc',
    'lavc', '-lavcopts', 'vcodec=mpeg4:vbitrate=800', '-o', 'prediction.mp4'])
    subprocess.call(['rm', '-rf', tmp_dir])
    #video = subprocess.Popen(['ffmpeg2theora -F %d -v 10 %s/screen%%04d.png -o' + outfile_name])
