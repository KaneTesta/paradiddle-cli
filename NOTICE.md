# Third-party notices

`vendor/PDUtilities` contains unmodified ParadiddleUtilities mappings and layout, obtained
from rrtrytcg/paradiddleTools commit `0754250dca14c13313286d5eaad88cae48239ea1`.
That repository identifies its ParadiddleUtilities source as commit `39d05fc`.
Copyright Emre Tanirgan and contributors; GNU GPL version 3 or later.
The CLI uses the rhythm-game YAML maps and default drum layout. Its conversion
implementation follows the official RLRR schema, with a separate merged MIDI
tempo evaluation and explicit delay handling. The upstream application remains
available at https://github.com/emretanirgan/ParadiddleUtilities.

The independent SNG parser implements the public mdsitton/SngFileFormat specification.
Enchor's public site JavaScript and the xlzipx/clone-hero-chart-manager source
were consulted to verify the public API; no chart-manager code is vendored.

Python runtimes and installed dependencies are not distributed in this
repository. Setup installs the versions listed in `requirements.txt`.
Their license notices are available in the installed packages.
FFmpeg is supplied by imageio-ffmpeg 0.6.0; its license notices are included
in that package. FFmpeg source: https://ffmpeg.org/download.html.

Downloaded song charts, audio, and artwork retain their respective owners'
rights. They are separate from this software's GPL license.
