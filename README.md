# Gramps2Gource

Blurring the line between Genealogy and Software Configuration Management visualisation.

[![Build Status](https://travis-ci.org/claws/gramps2gource.png?branch=master)](https://travis-ci.org/claws/gramps2gource)

## Overview

**Gramps2Gource** combines [Gramps](http://gramps-project.org/) (a Genealogy program written in Python) and [Gource](https://code.google.com/p/gource/) (a software version control visualisation tool for showing  changes over time) to help produce a novel family history visualisation. It parses exported `.gramps` files to produce a Gource custom log file containing the pedigree for a specified person. This custom log file can then be passed to Gource for rendering. See the example video below:

<a href="http://www.youtube.com/watch?feature=player_embedded&v=sPtTTv6d0s8
" target="_blank"><img src="http://i1.ytimg.com/vi/sPtTTv6d0s8/mqdefault.jpg"
alt="Gramps2Gource Example" border="10" /></a>


The Gource custom log format contains the following pipe ('|') delimited fields:

    timestamp - A unix timestamp of when the update occured.
    username  - The name of the user who made the update.
    type      - initial for the update type - (A)dded, (M)odified or (D)eleted.
    file      - Path of the file updated.
    colour    - A colour for the file in hex (FFFFFF) format. Optional.

Gramps2Gource works on Python2.7 and Python3.3.

One day I may investigate integrating this into Gramps as a plugin where it could access the Gramps database directly instead of via an exported `.gramps` file.

As always, garbage in garbage out. If your database is not well managed and consistent then your milage may vary.

This is really just a proof of concept. There is lots of cleanup that could be done and lots that could be added but it does what I wanted.

## Setup

### Install Gource

Gource can be installed using:

    $ sudo apt-get install gource

NOTE: Gource versions prior to v0.38 could not handle negative times (times before 1970). This was a real show stopper for displaying family history which is all based in the past. However, since version 0.38 this issue was resolved. In recent versions of Ubuntu the Gource version is v0.40 so this should not be a problem.

### Install Python Dependencies

#### Install Future module

Gramps2Gource uses dateutil to help parse complex date descriptions.

    $ [sudo] pip[3] install python-dateutil

#### Install Future module

For Python2 and Python3 compatibility Gramps2Gource uses the `future` module, hence this must be installed also.

    $ [sudo] pip[3] install future

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

To generate the custom gource log and display it you need to tell the `gramps2gource.py` script the focus person and the path to the Gramps database file. An output file containing the gource custom log will be saved to a file called `pedigree_<name>.log`.

Example:

    $ python gramps2gource.py --name="Amber Marie Smith" --db=example.gramps
    $ cat pedigree_amber_marie_smith.log | gource --load-config gource.conf -

The `gource.conf` effectively builds a command line similar to:

    $ cat pedigree_amber_marie_smith.log | gource -1280x720 --log-format custom --font-size 20 --hide users,dirnames,date --stop-at-end --camera-mode overview --seconds-per-day 1 --disable-bloom --auto-skip-seconds 1 -i 0 -c 3.0 -

The '-' at the end is important, it instructs Gource to read from standard input.


### Calendar Formats

Event dates can often be stored in different calendar formats. To accomodate
this it is possible to implement your own date parser to convert your specific
calendar date strings into the necessary datetime object used by Gramps2Gource.

Instead of running `gramps2gource.py` you will need to use something like the
`custom_date_g2g.py` example. This script accepts the same command line
arguments as the `gramps2gource.py` script.

Prior to running the script you will need to make some code changes to
implement and register your specific date handler functions.

For example, if you have event dates in `French Republican` format (e.g. the
`cformat` field stored within the gramps date item is `French Republican`) you
would create and register a handler with the name `French Republican`. For
example:

``` python

def frech_republican_date_handler(datestring):
    return magic_datetime_creater(datestring)

gramps.date_processor.register(
    'French Republican', french_republican_date_handler)
```

You need to register the date parser prior to instantiating the
`Gramps2Gource` object.


### Multiple Focus People

Multiple `name` arguments can be specified if you want to show more than one focus person. When multiple names are supplied the output file defaults to `pedigree.log`.

Example:

    $ python gramps2gource.py --name="Amber Marie Smith" --name="John Hjalmar Smith" --db=example.gramps
    $ cat pedigree.log | gource --load-config gource.conf --hide-root -



### Record Visualisation

To record the visualisation to a video file, the following commands may be useful.

h264:

    $ cat ~/path/to/custom_output.log | gource --load-config gource.conf -output-ppm-stream - --output-framerate 30 - | avconv -y -r 30 -f image2pipe -vcodec ppm -i - -b 8192K /path/to/video/output/file.mp4

webm:

    $ cat ~/path/to/custom_output.log | gource --load-config gource.conf -output-ppm-stream - | avconv -y -r 30 -f image2pipe -vcodec ppm -i - -vcodec libvpx -b 10000K /path/to/video/output/file.webm

[![Analytics](https://ga-beacon.appspot.com/UA-29867375-2/gramps2gource/readme?pixel)](https://github.com/claws/gramps2gource)
