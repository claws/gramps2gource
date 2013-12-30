# Gramps2Gource

Blurring the line between Genealogy and Software Configuration Management visualisation.

## Overview

[Gramps](http://gramps-project.org/) is a Genealogy program written in Python. [Gource](https://code.google.com/p/gource/) is a visualisation tool for showing software version control changes over time. **Gramps2Gource** combines these two tools to help produce a novel family history visualisation. It parses exported `.gramps` files to produce a Gource custom log file that contains the pedigree of a specified person. This file is then passed to Gource for rendering. See the example video below:

<center><a href="http://www.youtube.com/watch?feature=player_embedded&v=sPtTTv6d0s8
" target="_blank"><img src="http://i1.ytimg.com/vi/sPtTTv6d0s8/mqdefault.jpg"
alt="Gramps2Gource Example" width="240" height="180" border="10" /></a></center>


The Gource custom log format contains the following pipe ('|') delimited fields:

    timestamp - A unix timestamp of when the update occured.
    username  - The name of the user who made the update.
    type      - initial for the update type - (A)dded, (M)odified or (D)eleted.
    file      - Path of the file updated.
    colour    - A colour for the file in hex (FFFFFF) format. Optional.

One day I may investigate integrating this into Gramps as a plugin where it could access the Gramps database directly instead of via an exported `.gramps` file.

As always, garbage in garbage out. If your database is not well managed and consistent then your milage may vary.

This is really just a proof of concept. There is lots of cleanup that could be done and lots that could be added but it does what I wanted.

## Setup

### Install Gource

Gource can be installed using:

    $ sudo apt-get install gource

NOTE: Gource versions prior to v0.38 could not handle negative times (times before 1970). This was a real show stopper for displaying family history which is all based in the past. However, since version 0.38 this issue was resolved. In recent versions of Ubuntu the Gource version is v0.40 so this should not be a problem.


### Export a gramps file

    1. Open your Gramps family history database
    2. From the menu choose `Family Trees` then `Export...`
    3. In the dialog that opens click `Forward`.
    4. Select `Gramps XML (family tree)` then click forward.
    5. Click forward again as the defaults are OK.
    6. Choose a filename then click `Forward`.
    7. Click Apply.

### Download Gramps2Gource

	git clone https://github.com/claws/gramps2gource.git
	cd gramps2gource


## Using Gramps2Gource

Example:

    $ python gramps2gource.py --name="Joseph Blogs" --db=/path/to/filename.gramps

This will open the specified `.gramps` export file and extract pedigree information for the named person. It then saves the output to a file called pedigree_joseph_blogs.log.

To display this custom log output with Gource use:

    $ cat ~/path/to/custom_output.log | gource --load-config gource.conf -

This effectively runs the following long command line:

    $ cat ~/path/to/custom_output.log | gource -1280x720 --log-format custom --font-size 20 --hide users,dirnames,date --stop-at-end --camera-mode overview --seconds-per-day 1 --disable-bloom --auto-skip-seconds 1 -i 0 -c 3.0 -

The '-' at the end is important, it instructs Gource to read from standard input.

### Multiple Focus People

Multiple name arguments can be specified if you want to show more than one focus person. For example:

    $ python gramps2gource.py --name="Joseph Blogs" --name="Mary Poppins" --db=/path/to/filename.gramps
    $ cat ~/path/to/pedigree.log | gource --load-config gource.conf --hide-root -

When multiple names are supplied the output file defaults to `pedigree.log`.

### Record Visualisation

To record the visualisation to a video file, the following commands may be useful.

h264:

    $ cat ~/path/to/custom_output.log | gource --load-config gource.conf -output-ppm-stream - --output-framerate 30 - | avconv -y -r 30 -f image2pipe -vcodec ppm -i - -b 8192K /path/to/video/output/file.mp4

webm:

    $ cat ~/path/to/custom_output.log | gource --load-config gource.conf -output-ppm-stream - | avconv -y -r 30 -f image2pipe -vcodec ppm -i - -vcodec libvpx -b 10000K /path/to/video/output/file.webm
