#!/usr/bin/env python

'''
This script produces a custom Gource log file that can be passed to Gource for
it to display family history information. Currently it supports ancestors only.

Choose a focus person and pass this person's name along with the Gramps .gramps
file path to the script via command line arguments.

$ python gramps2gource.py --name="Focus Person" --db=path/to/filename.gramps

Then display the custom log using gource:

    $ cat /path/to/pedigree_<name>.log | gource -1280x720 --log-format custom
     --font-size 20 --hide users,dirnames,date --stop-at-end
     --camera-mode overview --seconds-per-day 1 --disable-bloom
     --auto-skip-seconds 1 -i 0 -c 3.0 -

The visualisation can be recorded to file using:

    $ cat /path/to/pedigree_<name>.log | gource -1280x720 --log-format custom
     --font-size 20 --hide users,dirnames,date --stop-at-end
     --camera-mode overview --seconds-per-day 1 --disable-bloom
     --auto-skip-seconds 1 -i 0 -c 3.0 -output-ppm-stream -
     --output-framerate 60 - | avconv -y -r 60 -f image2pipe -vcodec ppm -i -
     -b 8192K /path/to/pedigree_<name>.mp4

Author: Chris Laws
'''

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import open
from future.builtins import int

import datetime
import logging
import sys
import time

import gramps


ref_dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
ref_timestamp = time.mktime(ref_dt.timetuple())
try:
    secondsInOneDay = datetime.timedelta(days=1).total_seconds()
except AttributeError as ex:
    # python2.6 does not have total_seconds
    one_day_dt = datetime.timedelta(days=1)
    secondsInOneDay = (one_day_dt.microseconds + (one_day_dt.seconds + one_day_dt.days * 24 * 3600) * 10**6) / 10**6


GOURCE_ADDED = 'A'     # maps to birth
GOURCE_DELETED = 'D'   # maps to death
GOURCE_MODIFIED = 'M'  # maps to change
GOURCE_UNKNOWN = '?'   # maps to nothing


class Gramps2Gource(object):
    '''
    Create Gource custom logs from Gramps data files.
    '''

    def __init__(self, gramps_file):
        self.db = gramps.parser.parse(gramps_file)

    def get_ancestors(self, person, ancestors=None, gource_prefix=None):
        """
        Return an unordered list of tuples for this person and their
        ancestors. Each tuple contains a person handle and a pseudo-path
        to be used by Gource.
        """
        logging.debug("Collecting ancestors for {0}".format(person.name))

        if ancestors is None:
            ancestors = []

        # Construct a pseudo path from the person's unique handle.
        if gource_prefix:
            gource_prefix = "{0}/{1}".format(gource_prefix, person.handle)
        else:
            gource_prefix = person.handle

        person_name = person.name_with_dates
        gource_path = "{0}/{1}".format(gource_prefix, person_name)
        ancestors.append((person.handle, gource_path))

        if person.child_of_handle:
            family = self.db.get_family(person.child_of_handle)

            # walk up the father's tree
            if family.father:
                self.get_ancestors(family.father,
                                   ancestors=ancestors,
                                   gource_prefix=gource_prefix)

            # walk up the mother's tree
            if family.mother:
                self.get_ancestors(family.mother,
                                   ancestors=ancestors,
                                   gource_prefix=gource_prefix)

        return ancestors

    def pedigree(self, names, output_file):
        """
        Creates a custom Gource log containing the pedigree information for
        the specified names.
        """

        if not names:
            logging.error("No focus persons supplied")
            sys.exit(1)

        all_records = []

        for name in names:
            person_handles = []
            logging.info("Generating pedigree output for: {0}".format(name))
            person_handle = self.db.find_person(name)
            if person_handle:
                person = self.db.get_person(person_handle)
                ancestor_handles = self.get_ancestors(person)

                logging.debug("{0} has {1} ancestors in the database".format(
                    name, len(ancestor_handles)))
                person_handles = ancestor_handles

                if person_handles:
                    people_to_plot = []
                    for person_handle, person_gource_path in person_handles:
                        person = self.db.get_person(person_handle)
                        try:
                            associated_events = person.associated_events()
                        except TypeError:
                            associated_events = []

                        # Filter associated events to only include those with
                        # dates. Only dated events are useful when outputing
                        # a Gource formatted log.
                        associated_events_with_dates = []
                        for associated_event in associated_events:
                            obj, event, directEvent = associated_event
                            if event.date:
                                associated_events_with_dates.append(associated_event)

                        if associated_events_with_dates:
                            people_to_plot.append(
                                (person, person_gource_path,
                                 associated_events_with_dates))

                    if people_to_plot:
                        logging.info("Starting generation of custom gource log data")

                        records = self._to_pedigree_gource_log_format(people_to_plot)
                        all_records.extend(records)

                        logging.info("Finished generation of custom gource log data")

        if all_records:
            # Sort events by time such that Gource displays the pedigree in reverse order
            logging.info("Adjusting timestamps so gource displays them in reverse order")
            records = [(ts * -1, name, event, path) for ts, name, event, path in all_records]
            records.sort()

            logging.info("Writing custom gource log data to {0}".format(output_file))

            with open(output_file, 'w') as fd:
                for ts, name, event, path in records:
                    fd.write("{0}|{1}|{2}|{3}\n".format(ts, name, event, path))
                fd.write("\n") # add an empty line at the end to trigger EOF

            logging.info("Completed. Custom gource log file: {0}".format(output_file))

    def _to_gource_log_format(self, person_events):
        """
        Return a list of custom gource formatted log entries based on the list
        of person events passed in.
        """

        records = []

        for person, person_gource_path, related_events in person_events:

            logging.debug("Creating log entries for {0}".format(person.name))

            # Reduce events to only those that contain dates
            related_events_with_dates = []
            for related_event in related_events:
                person_family_object, event, directEvent = related_event
                if event.date:
                    related_events_with_dates.append(related_event)
                else:
                    logging.debug("No date for event {0}".format(event.type))

            if related_events_with_dates:

                for obj, event, directEvent in related_events_with_dates:

                    if event.datetime.year < ref_dt.year:
                        # Year is less than the epoch meaning we can't use
                        # time.mktime to create a useful timestamp for us.
                        # Instead, subtract the necessary seconds from the
                        # epoch time to arrive at the event time.
                        ref_delta = ref_dt - event.datetime
                        delta_seconds = ref_delta.total_seconds()
                        timestamp = ref_timestamp - delta_seconds
                    else:
                        timestamp = time.mktime(event.datetime.timetuple())

                    # Gource requires timestamp as an int
                    timestamp = int(timestamp)

                    if event.type == 'Birth':
                        if directEvent:
                            gource_event = GOURCE_ADDED
                        else:
                            gource_event = GOURCE_MODIFIED
                    elif event.type in ['Baptism', 'Christening']:
                        gource_event = GOURCE_MODIFIED
                    elif event.type == 'Death':
                        gource_event = GOURCE_DELETED
                    elif event.type in ['Burial', 'Cremation']:
                        gource_event = GOURCE_MODIFIED
                    elif event.type in ['Marriage', 'Marriage Banns']:
                        gource_event = GOURCE_MODIFIED
                    elif event.type == 'Census':
                        gource_event = GOURCE_MODIFIED
                    elif event.type in ["Divorce", 'Divorce Filing']:
                        gource_event = GOURCE_MODIFIED
                    elif event.type == "Electoral Roll":
                        gource_event = GOURCE_MODIFIED
                    elif event.type == "Emigration":
                        gource_event = GOURCE_MODIFIED
                    elif event.type in ["Residence", "Property"]:
                        gource_event = GOURCE_MODIFIED
                    elif event.type in ["Immigration", "Emmigration"]:
                        gource_event = GOURCE_MODIFIED
                    elif event.type == "Occupation":
                        gource_event = GOURCE_MODIFIED
                    elif event.type == "Probate":
                        gource_event = GOURCE_MODIFIED
                    else:
                        gource_event = GOURCE_UNKNOWN
                        logging.debug("Don't know how to handle event type {0}".format(event.type))

                    if gource_event != GOURCE_UNKNOWN:
                        record = (timestamp, person.surname.lower(),
                                  gource_event, person_gource_path)
                        records.append(record)

        records.sort()
        return records

    def _to_pedigree_gource_log_format(self, person_events):
        """
        Return a list of pedigree specific custom gource formatted log entries
        based on the list of person events passed in.
        """

        records = []

        for person, gource_path, related_events in person_events:

            logging.debug("Creating log entries for {0}".format(person.name))

            # Reduce events to only those that contain dates
            related_events_with_dates = []
            for related_event in related_events:
                person_family_object, event, directEvent = related_event
                if event.date:
                    related_events_with_dates.append(related_event)
                else:
                    logging.debug("No date for event {0}".format(event.type))

            if related_events_with_dates:

                for obj, event, directEvent in related_events_with_dates:

                    if event.datetime.year < ref_dt.year:
                        # Year is less than the epoch meaning we can't use
                        # time.mktime to create a useful timestamp for us.
                        # Instead, subtract the necessary seconds from the
                        # epoch time to arrive at the event time.
                        ref_delta = ref_dt - event.datetime
                        delta_seconds = ref_delta.total_seconds()
                        timestamp = ref_timestamp - delta_seconds
                    else:
                        timestamp = time.mktime(event.datetime.timetuple())

                    # Gource requires timestamp as an int
                    timestamp = int(timestamp)

                    # For this particular application we only want to capture
                    # the birth (ADDED) event.

                    if event.type == 'Birth':
                        if directEvent:
                            gource_event = GOURCE_ADDED
                            record = (timestamp, person.surname.lower(),
                                      gource_event, gource_path)
                            records.append(record)

        records.sort()
        return records


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Create Gource custom logs from Gramps data")
    parser.add_argument("-d", "--db", dest="database", default=None,
                        type=str,
                        help="The gramps database file to use")
    parser.add_argument("-n", "--names", action='append', dest="names",
                        default=None, type=str,
                        help="The focus person to extract pedigree data for")
    parser.add_argument("-o", "--output", dest="output", default=None,
                        type=str,
                        help="The name of the file to send the output to")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s - %(message)s')

    if args.database is None:
        print("Error: No gramps file provided")
        args.print_usage()
        sys.exit(1)

    if args.names is None:
        print("Error: No focus name(s) provided")
        args.print_usage()
        sys.exit(1)

    if args.output is None:
        if len(args.names) > 1:
            args.output = "pedigree.log"
        else:
            lower_name = args.names[0].lower().replace(" ", "_")
            args.output = "pedigree_{0}.log".format(lower_name)

    g2g = Gramps2Gource(args.database)
    g2g.pedigree(args.names, args.output)

    logging.info("Done.")
