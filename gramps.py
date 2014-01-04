#!/usr/bin/env python

'''
This module implements a simple and naive Gramps XML file (.gramps) parser.

Author: Chris Laws
'''

from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import str

import datetime
import dateutil.parser
import gzip
import logging
import sys
try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree

# In python2.6 the GzipFile does not have __exit__ so does
# not work with the with statement.
_required_version = (2.6)
_py_ver = sys.version_info
print("Python version is: {0}".format(_py_ver))
if _py_ver == 2:
    if _py_ver[1] < 6:
        print("Error: Python version must be {0}.{1} or greater",
              _required_version[0], _required_version[1])
        sys.exit(1)

    if _py_ver[1] == 6:

        class GzipFileForPy26(gzip.GzipFile):

            def __enter__(self):
                return self

            def __exit__(self, type, value, tb):
                self.close()

        print("Using GzipFileForPy26 as GzipFileReader for python version: {0}".format(_py_ver))
        GzipFileReader = GzipFileForPy26
    else:
        # python 2.7+
        print("Using GzipFile as GzipFileReader for python version: {0}".format(_py_ver))
        GzipFileReader = gzip.GzipFile
else:
    # python3+
    print("Using GzipFile as GzipFileReader for python version: {0}".format(_py_ver))
    GzipFileReader = gzip.GzipFile

indent = "  "


def generate_timestring(dt):
    '''
    Required because datetime.strftime barfs on years prior to 1900
    '''
    format = "%Y-%m-%d"
    if dt.year > 1900:
        return dt.strftime(format)
    else:
        format = format.replace('%Y', str(dt.year))
        dt = datetime.datetime(1900, dt.month, dt.day, dt.hour,
                               dt.minute, dt.second)

    return dt.strftime(format)


class Place(object):
    '''
    A Gramps place object.

    Example of a Gramps place structure:

      <places>
       <placeobj handle="_bcd2a83849845c12c13" change="1297580946" id="P0806">
         <ptitle>Morwell, Victoria, Australia</ptitle>
         <coord long="146.3947107" lat="-38.2345742"/>
       </placeobj>
    '''

    def __init__(self, store):
        self.store = store
        self.handle = None
        self.id = None
        self.type = None
        self.title = None
        self.lat = None
        self.lon = None

    @property
    def coordinates(self):
        '''
        Return a tuple of lat, lon for the location
        '''
        if self.lat and self.lon:
            return (self.lat, self.lon)
        return None

    def __str__(self):
        o = []
        o.append("Place")
        title = ""
        if self.title:
            title = self.title
        lat_lon = ""
        if self.lat and self.lon:
            lat_lon = " (lat={0}, lon={1})".format(self.lat, self.lon)
        o.append("{0}{1}{2}".format(indent, title, lat_lon))
        return "\n".join(o)


class Event(object):
    '''
    A Gramps event object.

    Example of a Gramps event structure:

    <event handle="_bb2a73da89376f2e069" change="1287656448" id="E1000">
     <type>Death</type>
     <dateval val="1955-06-04"/>
     <place hlink="_bb2a73da908569b4132"/>
     <noteref hlink="_bb2a73da9362223d031"/>
     <sourceref hlink="_bb60df55dd862a3e6b1" conf="4">
       <spage>1955/012559</spage>
       <noteref hlink="_bb60eb134ff61992598"/>
       <dateval val="1955-06-04"/>
     </sourceref>
    </event>

    '''

    def __init__(self, store):
        self.store = store
        self.handle = None
        self.id = None
        self.type = None
        self.description = None
        self.date = None
        self.date_type = None

        # handles
        self.place_handle = None
        self.note_handles = []
        self.source_handles = []

    @property
    def datetime(self):
        '''
        Return a datetime object for this event date
        '''
        if self.date:
            try:
                parts = self.date.split("-")
                if len(parts) == 2:
                    logging.debug("{0} missing item from date string, using day 01 for compatibility".format(self.date))
                    self.date = "{0}-01".format(self.date)
                # Dates are used in many different formats, use the
                # dateutil parser in an effort to successfully
                # parse a useful date.
                dt = dateutil.parser.parse(self.date)
                return dt
            except ValueError as ex:
                logging.error("Problem date \'{0}\':".format(self.date, ex))
                raise Exception(ex)
        else:
            return None

    def datetime_as_string(self):
        return generate_timestring(self.datetime)

    @property
    def place(self):
        if self.place_handle:
            return self.store.get_place(self.place_handle)
        return None

    def __str__(self):
        o = []
        o.append("Event")

        dateStr = "unknown"
        if self.date:
            if self.date_type:
                dateStr = "{0} {1}".format(self.date_type, self.date)
            else:
                dateStr = self.date

        o.append("{0}{1}, {2}".format(indent, self.type, dateStr))

        placeStr = "unknown"
        if self.place:
            thePlace = self.store.get_place(self.place)
            if thePlace:
                p = []
                for line in str(thePlace).split("\n"):
                    p.append("{0}{1}".format(indent, line))
                placeStr = "\n".join(p)
                o.append(placeStr)
        else:
            o.append("{0}Place".format(indent * 2))
            o.append("{0}None".format(indent * 3))

        if self.description:
            o.append("{0}description={1}".format(indent, self.description))

        return "\n".join(o)


class Person(object):
    '''
    A person object
    '''

    def __init__(self, store):
        self.store = store
        self.handle = None
        self.id = None
        self.gender = None
        self.firstnames = []
        self.prefix = None
        self.surname = None
        self._birth = None
        self._death = None

        # handles
        self.event_handles = []
        self.child_of_handle = None
        self.parent_in_handles = []
        self.notes = []
        self._events = None

    @property
    def name(self):
        '''
        Return a string containing the full name of this person
        i.e. firstname middlenames surname
        '''
        if len(self.firstnames) > 1:
            firstnames = " ".join(self.firstnames)
        else:
            firstnames = "".join(self.firstnames)
        return "{0} {1}".format(firstnames, self.surname)

    @property
    def name_with_dates(self):
        '''
        Return a string containing this persons name and their
        birth and death dates.
        i.e firstname surname (b. date, d. date)
        '''
        if self.death is None:
            return "{0} (b. {1})".format(self.name, self.birth)
        else:
            return "{0} (b. {1}, d. {2})".format(self.name,
                                                 self.birth,
                                                 self.death)

    @property
    def birth(self):
        '''
        Return a birth date string for this person (if available).
        Include any prefixes such as bef, aft, abt, etc.
        '''
        if self._birth is None:
            # search through events
            for event in self.events:
                if event.type == 'Birth':
                    if event.date:
                        if event.date_type:
                            self._birth = "{0} {1}".format(event.date_type,
                                                           event.date)
                        else:
                            self._birth = event.date
                    else:
                        self._birth = "unknown"

        return self._birth

    @property
    def birth_datetime(self):
        '''
        Return a birth date string for this person (if available).
        Include any prefixes such as bef, aft, abt, etc.
        '''
        # search through events
        for event in self.events:
            if event.type == 'Birth':
                return event.datetime
        return None

    @property
    def death(self):
        '''
        Return a death date string for this person (if available).
        Include any prefixes such as bef, aft, abt, etc.
        '''
        if self._death is None:
            # search through events
            for event in self.events:
                if event.type == 'Death':
                    if event.date:
                        if event.date_type:
                            self._death = "{0} {1}".format(event.date_type,
                                                           event.date)
                        else:
                            self._death = event.date
                    else:
                        self._death = "unknown"

        return self._death

    @property
    def death_datetime(self):
        '''
        Return a death date string for this person (if available).
        Include any prefixes such as bef, aft, abt, etc.
        '''
        # search through events
        for event in self.events:
            if event.type == 'Death':
                return event.datetime
        return None

    @property
    def events(self):
        if self._events is None:
            self._events = []
            if self.event_handles:
                for event_handle in self.event_handles:
                    event = self.store.get_event(event_handle)
                    self._events.append(event)
        return self._events

    def associated_events(self, includeEventsWithNoDate=False):
        '''
        Return a time ordered list of tuples for each event that this person
        was involved with. This set includes direct event involvement
        (eg. birth) and indirect involvement (eg. birth of younger sibling).

        Each item in the list is a tuple containing a Person or Family object
        and an Event object.
        '''

        dated_events = []
        undated_events = []

        SiblingCutoffDatetime = None
        directPersonEvent = True

        for event in self.events:
            if event.datetime:
                if event.type in ['Immigration', 'Emmigration']:
                    # This flag is used later to ensure we don't associate
                    # siblings with this person's events after an immigration
                    # event as it is assumed that the person would not be
                    # involved/around these events.
                    SiblingCutoffDatetime = event.datetime
                dated_events.append((self, event, directPersonEvent))
            else:
                if includeEventsWithNoDate:
                    undated_events.append((self, event, directPersonEvent))
                else:
                    logging.debug("Discarding direct person event {0} for {1} as it has no date".format(event.type, self.name))
                    pass

        # now retrieve associated events that this person was involved with
        directPersonEvent = False

        if self.parent_in_handles:
            logging.debug("{0} is a parent in {1} families".format(self.name, len(self.parent_in_handles)))
            for parent_handle in self.parent_in_handles:
                family = self.store.get_family(parent_handle)
                # Add any family events such as marriage, divorce
                logging.debug("Family {0} has {1} family events".format(family.name, len(family.events)))
                for event in family.events:
                    if event.datetime:
                        dated_events.append((family, event, directPersonEvent))
                    else:
                        if includeEventsWithNoDate:
                            undated_events.append((family, event, directPersonEvent))
                        else:
                            logging.debug("Discarding associated family event {0} for {1} as it has no date".format(event.type, family.name))
                            pass

                logging.debug("Family {0} has {1} children".format(family.name, len(family.children)))
                # add birth of children
                if family.children:
                    for child in family.children:
                        for event in child.events:
                            if event.type == 'Birth':
                                if event.datetime:
                                    dated_events.append((child, event, directPersonEvent))
                                else:
                                    if includeEventsWithNoDate:
                                        undated_events.append((child, event, directPersonEvent))
                                    else:
                                        logging.debug("Discarding associated family event {0} for {1} as it has no date" % (event.type, child.name))
                                        pass

        if self.child_of_handle:
            # potentially associate younger sibling location events too
            # as this person was likely around those locations too.
            family = self.store.get_family(self.child_of_handle)
            logging.debug("Family {0} had {1} children".format(family.name, len(family.children)))
            for sibling in family.children:
                if sibling.handle != self.handle:
                    for event in sibling.events:
                        if event.type == 'Birth':
                            if event.datetime:
                                if event.datetime > self.birth_datetime:
                                    # don't associate sibling birth events if they
                                    # occur after the person has immigrated/emmigrated.
                                    if SiblingCutoffDatetime is None:
                                        dated_events.append((sibling, event, directPersonEvent))
                                    else:
                                        if event.datetime < SiblingCutoffDatetime:
                                            dated_events.append((sibling, event, directPersonEvent))
                            else:
                                if includeEventsWithNoDate:
                                    undated_events.append((sibling, event, directPersonEvent))
                                else:
                                    logging.debug("Discarding associated family event {0} for {1} as it has no date" % (event.type, sibling.name))
                                    pass

        # sort events in time order. This can only be done after
        # making sure that we only have events with dates.
        def get_datetime(dated_event_tuple):
            person_or_family_object, event, directEvent = dated_event_tuple
            return event.datetime

        dated_events.sort(key=get_datetime)

        events = dated_events

        # tack undated events onto end of time ordered list if requested
        if includeEventsWithNoDate:
            events.extend(undated_events)

        return events

    def ancestors(self, ancestors=None):
        """
        Return an unordered list of this person's handle and those of their
        ancestors.
        """
        logging.debug("Collecting ancestors for {0}".format(self.name))
        if ancestors is None:
            ancestors = []
        ancestors.append(self.handle)

        if self.child_of_handle:
            family = self.store.get_family(self.child_of_handle)

            # walk up the father's tree
            if family.father:
                family.father.ancestors(ancestors)

            # walk up the mother's tree
            if family.mother:
                family.mother.ancestors(ancestors)

        return ancestors

    def descendents(self):
        '''
        Return an unordered list of this person's handle and those of their
        descendents.
        '''
        raise NotImplementedError

    def __str__(self):
        o = []
        o.append("Person")
        o.append("{0}{1}".format(indent, self.name_with_dates))

        if self.child_of_handle:
            theFamily = self.store.get_family(self.child_of_handle)
            o.append("{0}Child of {1}".format(indent, theFamily.name))
        else:
            o.append("{0}Child of unknown".format(indent))

        if self.parent_in_handles:
            for p in self.parent_in_handles:
                theFamily = self.store.get_family(p)
                o.append("{0}Parent in {1}".format(indent, theFamily.name))
        if self.events:
            o.append("{0}Events:".format(indent))
            indent2 = indent * 2
            lines = []
            for event in self.events:
                for line in str(event).split("\n"):
                    lines.append("{0}{1}".format(indent2, line))
                eventStr = "\n".join(lines)
                o.append(eventStr)

        return "\n".join(o)


class Family(object):
    '''
    A Gramps family object

    Example of a Gramps family structure:

    <family handle="_bbd9a6fc3005c442174" change="1296473477" id="F0414">
     <rel type="Unknown"/>
     <father hlink="_bbd9a89f2d86cb5d966"/>
     <mother hlink="_bbd9aa0bf5828e2063d"/>
     <eventref hlink="_bbd9aac4f234de2e484" role="Family"/>
     <childref hlink="_bbd99985f4654c844c2"/>
     <childref hlink="_bbd9b4d182d06ba9642"/>
     <childref hlink="_bbd9b59cb0709454032"/>
     <childref hlink="_bbd9b32db1501cb7968"/>
     <childref hlink="_bbd9fd3f1404b1ac595"/>
    </family>

    '''

    def __init__(self, store):
        self.store = store
        self.handle = None
        self.id = None
        self.father_handle = None
        self.mother_handle = None
        self.relationship = None

        self.event_handles = []
        self.children_handles = []
        self.step_children_handles = []
        self.source_handles = []
        self._mother = None
        self._father = None
        self._children = None
        self._events = None

    @property
    def name(self):
        '''
        Return a string containing the father and mother name for this family
        '''
        if self.mother:
            m = self.mother.name
        else:
            m = "unknown"

        if self.father:
            f = self.father.name
        else:
            f = "unknown"

        family_name = "{0} & {1}".format(f, m)
        return family_name

    @property
    def name_with_dates(self):
        '''
        Return a string containing the father and mother name of this family
        which include the birth and death dates.
        '''
        if self.mother:
            m = self.mother.name_with_dates
        else:
            m = "unknown"

        if self.father:
            f = self.father.name_with_dates
        else:
            f = "unknown"

        family_name = "{0} & {1}".format(f, m)
        return family_name

    @property
    def mother(self):
        if self._mother is None:
            # search for mother person
            if self.mother_handle:
                self._mother = self.store.get_person(self.mother_handle)
        return self._mother

    @property
    def father(self):
        if self._father is None:
            # search for father person
            if self.father_handle:
                self._father = self.store.get_person(self.father_handle)
        return self._father

    @property
    def children(self):
        if self._children is None:
            self._children = []
            if self.children_handles:
                # search for children persons
                for child_handle in self.children_handles:
                    child = self.store.get_person(child_handle)
                    if child:
                        self._children.append(child)
        return self._children

    @property
    def events(self):
        if self._events is None:
            self._events = []
            if self.event_handles:
                for event_handle in self.event_handles:
                    event = self.store.get_event(event_handle)
                    self._events.append(event)
        return self._events

    def __str__(self):
        o = []
        o.append("Family")
        o.append("{0}{1}".format(indent, self.name_with_dates))
        o.append("{0}relationship={1}".format(indent, self.relationship))

        # TODO: display eventref here

        if self.children:
            o.append("{0}Children:".format(indent))
            indent2 = indent * 2
            for child in self.children:
                indented_child_lines = []
                for line in str(child).split("\n"):
                    indented_child_lines.append("{0}{1}".format(indent2, line))
                childStr = "\n".join(indented_child_lines)
                o.append(childStr)
        else:
            o.append("{0}Children: None".format(indent))

        return "\n".join(o)


class Store(object):
    '''
    Stores information extracted by the Gramps database parser
    '''

    def __init__(self):
        self.persons = {}
        self.families = {}
        self.events = {}
        self.places = {}
        self.notes = {}
        self.sources = {}

    def get_person(self, handle):
        '''
        Return the person with the specified handle
        '''
        return self.persons.get(handle, None)

    def get_family(self, handle):
        '''
        Return the family with the specified handle
        '''
        return self.families.get(handle, None)

    def get_event(self, handle):
        '''
        Return the event with the specified handle
        '''
        return self.events.get(handle, None)

    def get_place(self, handle):
        '''
        Return the place with the specified handle
        '''
        return self.places.get(handle, None)

    def get_source(self, handle):
        '''
        Return the source with the specified handle
        '''
        return self.sources.get(handle, None)

    def get_note(self, handle):
        '''
        Return the note with the specified handle
        '''
        return self.notes.get(handle, None)

    def find_person(self, search_name):
        '''
        Return the handle for the first person found with a
        matching name.
        Return None if no match is found.
        '''
        logging.debug("Searching for {0}".format(search_name))
        search_person_handle = None
        for person_handle in self.persons:
            person = self.get_person(person_handle)
            if person.name == search_name:
                search_person_handle = person.handle
                logging.debug("Found {0} with handle {1}".format(search_name,
                                                                 person.handle))
                break
        return search_person_handle


class NS:
    '''
    Namespace helper to append the gramps namespace onto tags.
    This makes writing the search paths easier.
    '''
    def __init__(self, uri):
        self.uri = uri

    def __getattr__(self, tag):
        return self.uri + tag

    def __call__(self, path):
        prefix = None
        if path.startswith(".//"):
            items = path[3:].split("/")
            prefix = './/'
        else:
            items = path.split("/")

        ns_tags = []
        for tag in items:
            ns_tag = getattr(self, tag)
            ns_tags.append(ns_tag)
        ns_path = "/".join(ns_tags)

        if prefix:
            ns_path = './/' + ns_path

        return ns_path


def to_pretty_xml(elem):
    """
    Return a pretty-printed XML string for the Element.
    """
    from xml.dom import minidom
    rough_string = etree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


class Parser(object):

    def parse(self, gramps_file):
        """
        @return: a store object populated with content extracted from the database.
        """

        logging.info("Loading Gramps database from {0}".format(gramps_file))

        store = Store()

        with GzipFileReader(filename=gramps_file, mode="rb", compresslevel=9) as fd:
            data = fd.read()

            root = etree.fromstring(data)

            # Detect the namespace so we know what to place in front
            # of the known tag names.
            detected_namespace = ""
            items = root.tag.split("}")
            if len(items) == 2:
                namespace_candidate, tag = items
                if "{" in namespace_candidate:
                    # There is a namespace prefix
                    detected_namespace = '{%s}' % namespace_candidate[1:]

            GrampsNS = NS(detected_namespace)

            # Extract person entries into Person objects and store them
            # in the persons dict keyed by the person's handle.
            #
            personNodes = root.findall(GrampsNS('.//people/person'))

            for personNode in personNodes:
                p = Person(store)
                p.id = personNode.attrib.get('id')

                genderNode = personNode.find(GrampsNS('gender'))
                p.gender = genderNode.text

                handle = personNode.attrib.get('handle')
                p.handle = handle
                store.persons[handle] = p

                nameNode = personNode.find(GrampsNS('name'))
                if nameNode:

                    firstnameNode = nameNode.find(GrampsNS('first'))
                    if firstnameNode is not None:
                        p.firstnames = firstnameNode.text.split(" ")
                    else:
                        pass  # No first name node found

                    surnameNode = nameNode.find(GrampsNS('surname'))
                    if surnameNode is not None:
                        p.surname = surnameNode.text
                        p.prefix = surnameNode.attrib.get('prefix')
                    else:
                        pass  # No surname node found
                else:
                    pass  # No name node found

                for eventNode in personNode.findall(GrampsNS('eventref')):
                    event_handle = eventNode.attrib.get('hlink')
                    p.event_handles.append(event_handle)

                for parentinNode in personNode.findall(GrampsNS('parentin')):
                    parentin_handle = parentinNode.attrib.get('hlink')
                    p.parent_in_handles.append(parentin_handle)

                childofNode = personNode.find(GrampsNS('childof'))
                if childofNode is not None:
                    p.child_of_handle = childofNode.attrib.get('hlink')

                for noteNode in personNode.findall(GrampsNS('noteref')):
                    note_handle = noteNode.attrib.get('hlink')
                    p.notes.append(note_handle)

            familyNodes = root.findall(GrampsNS('.//families/family'))

            for familyNode in familyNodes:
                f = Family(store)
                f.id = familyNode.attrib.get('id')

                motherNode = familyNode.find(GrampsNS('mother'))
                if motherNode is not None:
                    f.mother_handle = motherNode.attrib.get('hlink')

                fatherNode = familyNode.find(GrampsNS('father'))
                if fatherNode is not None:
                    f.father_handle = fatherNode.attrib.get('hlink')

                relationshipNode = familyNode.find(GrampsNS('rel'))
                if relationshipNode is not None:
                    f.relationship = relationshipNode.attrib.get('type')

                for eventNode in familyNode.findall(GrampsNS('eventref')):
                    f.event_handles.append(eventNode.attrib.get('hlink'))

                handle = familyNode.attrib.get('handle')
                f.handle = handle
                store.families[handle] = f

                for childNode in familyNode.findall(GrampsNS('childref')):
                    child_handle = childNode.attrib.get('hlink')
                    if childNode.attrib.get('frel') == 'Stepchild':
                        f.step_children_handles.append(child_handle)
                    else:
                        f.children_handles.append(child_handle)

                for sourceNode in familyNode.findall(GrampsNS('sourceref')):
                    source_handle = sourceNode.attrib.get('hlink')
                    f.source_handles.append(source_handle)

            eventNodes = root.findall(GrampsNS('.//events/event'))

            for eventNode in eventNodes:
                e = Event(store)
                e.id = personNode.attrib.get('id')

                handle = eventNode.attrib.get('handle')
                e.handle = handle
                store.events[handle] = e

                typeNode = eventNode.find(GrampsNS('type'))
                if typeNode is not None:
                    e.type = typeNode.text

                datevalNode = eventNode.find(GrampsNS('dateval'))
                if datevalNode is not None:
                    e.date = datevalNode.attrib.get('val')
                    e.date_type = datevalNode.attrib.get('type')

                descriptionNode = eventNode.find(GrampsNS('description'))
                if descriptionNode is not None:
                    e.description = descriptionNode.text

                placeNode = eventNode.find(GrampsNS('place'))
                if placeNode is not None:
                    e.place_handle = placeNode.attrib.get('hlink')

                for noteNode in eventNode.findall(GrampsNS('noteref')):
                    note_handle = noteNode.attrib.get('hlink')
                    e.note_handles.append(note_handle)

                for sourceNode in eventNode.findall(GrampsNS('sourceref')):
                    source_handle = sourceNode.attrib.get('hlink')
                    e.source_handles.append(source_handle)

            placeNodes = root.findall(GrampsNS('.//places/placeobj'))

            for placeNode in placeNodes:
                p = Place(store)
                p.id = placeNode.attrib.get('id')

                handle = placeNode.attrib.get('handle')
                p.handle = handle
                store.places[handle] = p

                titleNode = placeNode.find(GrampsNS('ptitle'))
                if titleNode is not None:
                    p.title = titleNode.text

                coordNode = placeNode.find(GrampsNS('coord'))
                if coordNode is not None:
                    p.lat = coordNode.attrib.get('lat')
                    p.lon = coordNode.attrib.get('long')

            # TODO:
            # extract sources
            # extract notes
            # etc

            return store

parser = Parser()
