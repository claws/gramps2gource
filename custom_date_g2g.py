
import argparse
import logging
import sys

import gramps
from gramps2gource import Gramps2Gource


logger = logging.getLogger(__name__)


def my_date_handler(datestring):
    ''' Implement your custom date parser here.

    :param datestring: a date string containg a date in a particular calendar
      format.

    :return: a datetime object representing the date.
    '''
    raise NotImplementedError


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


if __name__ == "__main__":

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format='%(levelname)s - %(message)s')

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

    gramps.date_processor.register('my_cal_format', my_date_handler)
    g2g = Gramps2Gource(args.database)
    g2g.pedigree(args.names, args.output)

    logger.info("Done.")
