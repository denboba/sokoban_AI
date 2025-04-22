import cv2
import os
import argparse
from PIL import Image
import numpy as np


def gif_to_video(gif_path, fps=24):
    try:
        # Open the GIF file using PIL
        gif = Image.open(gif_path)

        # Get dimensions from first frame
        gif.seek(0)
        width, height = gif.size

        # Build output path from input path
        input_dir = os.path.dirname(gif_path)
        input_name = os.path.splitext(os.path.basename(gif_path))[0]
        output_path = os.path.join(input_dir, f"{input_name}.mp4")

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        print(f"Converting {gif_path} to {output_path} (estimated {gif.n_frames} frames at {fps} FPS)...")

        # Process each frame
        for frame_idx in range(gif.n_frames):
            try:
                gif.seek(frame_idx)
                frame = np.array(gif.convert('RGB'))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                video.write(frame)

                if frame_idx % 100 == 0:
                    print(f"Processed frame {frame_idx + 1}/{gif.n_frames}")

            except EOFError:
                break  # End of GIF

        video.release()
        print(f"Successfully converted GIF to {output_path}")

    except Exception as e:
        print(f"Error converting GIF: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert GIF to MP4 video')
    parser.add_argument('input_gif', help='Path to input GIF file')
    parser.add_argument('-f', '--fps', type=int, default=24, help='Frames per second (default: 24)')

    args = parser.parse_args()

    if '*' in args.input_gif:
        import glob
        gif_files = glob.glob(args.input_gif)
        if not gif_files:
            print(f"Error: No files found matching pattern '{args.input_gif}'")
            exit(1)
        args.input_gif = gif_files[0]

    if os.path.exists(args.input_gif):
        gif_to_video(args.input_gif, fps=args.fps)
    else:
        print(f"Error: Input file '{args.input_gif}' not found.")
