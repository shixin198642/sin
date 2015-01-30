#!/usr/bin/env python

'''Python client library for Sin'''

from datetime import datetime
import cookielib
import datetime
import json
import logging  
import os
import re
import sys
import time
import time
import urllib
import urllib2

from sensei import BQLRequest, SenseiClientError, SenseiFacet, SenseiSelection,\
                   SenseiSort, SenseiFacetInitParams, SenseiFacetInfo,\
                   SenseiNodeInfo, SenseiSystemInfo, SenseiRequest, SenseiHit,\
                   SenseiResultFacet, SenseiResult, SenseiClient

from optparse import OptionParser
import getpass

logger = logging.getLogger('sin_client')  
store_map = {}

# Datetime regular expression
DATE_TIME = r'''(["'])(\d\d\d\d)([-/\.])(\d\d)\3(\d\d) (\d\d):(\d\d):(\d\d)\1'''
DATE_TIME_REGEX = re.compile(DATE_TIME)

class Sindex:
  opener = None
  name = None
  senseiClient = None
  baseurl = None
  config = None
  created = None
  description = None
  status = None
  
  def __init__(self, id, name, api_key, description, created, url, config, senseiClient, status, cookie_jar):
    self.id = id
    self.name = name
    self.api_key = api_key
    self.created = created
    self.description = description
    self.senseiClient = senseiClient
    self.cookie_jar = cookie_jar
    self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
    self.opener.addheaders = [('X-Sin-Api-Key', api_key)]
    self.baseurl = url
    self.config = config
    self.status = status
  
  def available(self):
    '''Check if the store is available.'''
    url = '%s/%s/%s' % (self.baseurl,'available',self.name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('available',False)

  def start(self):
    '''Start the store.'''
    url = '%s/%s/%s' % (self.baseurl,'start-store',self.name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))

  def stop(self):
    '''Stop the store.'''
    url = '%s/%s/%s' % (self.baseurl,'stop-store',self.name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
  
  def addDoc(self,doc):
    '''Add a document to the store.'''
    return self.addDocs([doc])

  def addDocs(self,docs):
    '''Add a list of documents.'''
    if not docs:
      raise Exception('no docs supplied')
    url = '%s/%s/%s' % (self.baseurl,'add-docs',self.name)

    params = urllib.urlencode({'docs': json.dumps(docs)})
    urlReq = urllib2.Request(url,params)
    res = self.opener.open(urlReq)

    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('numPosted',0)

  def updateDoc(self,doc):
    '''Update a document.'''
    if not doc:
      raise Exception('no doc supplied')
    url = '%s/%s/%s' % (self.baseurl,'update-doc',self.name)

    params = urllib.urlencode({'doc': json.dumps(doc)})
    urlReq = urllib2.Request(url,params)
    res = self.opener.open(urlReq)

    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('numPosted',0)
    
  def importFile(self,dataFile,batchSize=100):
    batch = []
    fd = open(dataFile,'r+')
    for line in fd:
      jsonObj = dict(json.loads(line))
      batch.append(jsonObj)
      if batch.length >= batchSize:
        self.addDocs(batch)
        batch = []
    fd.close()
    if batch.length > 0:
      self.addDocs(batch)

    
  def getDoc(self, id):
    '''Retrieve a document based its document ID.'''
    if not id:
      return None

    req = SenseiRequest()
    sel = SenseiSelection('_uid')
    sel.addSelection(str(id))
    req.count = 1
    req.fetch_stored = True
    req.selections['_uid'] = sel
    res = self.senseiClient.doQuery(req)
    doc = None
    if res.numHits > 0:
      if res.hits and len(res.hits) > 0:
        hit = res.hits[0]
        doc = hit.get('_srcdata')
    if doc:
      return doc
    else:
      return None

  def delDoc(self,id):
    '''Delete a document based on the document ID.

    Return 1 if the document is deleted successfully; 0 otherwise.
    
    '''
    return self.delDocs([id])

  def delDocs(self, idList):
    '''Delete multiple documents based on a list of document IDs.

    Return the number of documents deleted successfully.

    '''
    if not idList or len(idList)==0:
      return 0

    url = '%s/%s/%s' % (self.baseurl,'delete-docs',self.name)
    params = urllib.urlencode({'ids': idList})
    urlReq = urllib2.Request(url, params)
    res = self.opener.open(urlReq)

    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error', 'unknown error'))
    return jsonObj.get('numDeleted', 0)

  def getSize(self):
    req = SenseiRequest()
    req.count = 0
    res = self.senseiClient.doQuery(req)
    return res.totalDocs
  
  def getSenseiClient(self):
    return self.senseiClient

#
# BQL Parser for DDL and some DML statements
#

from pyparsing import Literal, CaselessLiteral, Word, Upcase, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, ParseFatalException, ParseSyntaxException, \
    Forward, oneOf, quotedString, \
    ZeroOrMore, restOfLine, Keyword, OnlyOnce, Suppress, removeQuotes, NotAny, OneOrMore, \
    MatchFirst, Regex, stringEnd, operatorPrecedence, opAssoc

class BQLParser:
  '''BQL Parser for DDL and some DML statments.

  This parser is used at the Sin client level to parser DDL statements
  like CREATE TABLE, ALTER TABLE and DML statements like INSERT, UPDATE,
  DELETE.

  '''

  def __init__(self):
    self._parser = self._build_parser()
    self.time_now = None

  def parse(self, bql_stmt):
    tokens = None
    try:
      self.time_now = int(time.time() * 1000)
      tokens = self._parser.parseString(bql_stmt, parseAll=True)
    except ParseException as err:
      raise err
    except ParseSyntaxException as err:
      raise err
    except ParseFatalException as err:
      raise err
    finally:
      pass
      # self.reset_all()
    return tokens

  def convert_time(self, s, loc, toks):
    '''Convert a time expression into an epoch time.'''
  
    if toks[0] == 'now':
      return self.time_now
    elif toks.date_time_regex:
      mm = DATE_TIME_REGEX.match(toks[0])
      (_, year, _, month, day, hour, minute, second) = mm.groups()
      try:
        time_stamp = datetime.strptime('%s-%s-%s %s:%s:%s' % (year, month, day, hour, minute, second),
                                       '%Y-%m-%d %H:%M:%S')
      except ValueError as err:
        raise ParseSyntaxException(ParseException(s, loc, 'Invalid date/time string: %s' % toks[0]))
      return int(time.mktime(time_stamp.timetuple()) * 1000)
  
  def convert_time_span(self, s, loc, toks):
    '''Convert a time span expression into an epoch time.'''
  
    total = 0
    if toks.week_part:
      total += toks.week_part[0] * 7 * 24 * 60 * 60 * 1000
    if toks.day_part:
      total += toks.day_part[0] * 24 * 60 * 60 * 1000
    if toks.hour_part:
      total += toks.hour_part[0] * 60 * 60 * 1000
    if toks.minute_part:
      total += toks.minute_part[0] * 60 * 1000
    if toks.second_part:
      total += toks.second_part[0] * 1000
    if toks.millisecond_part:
      total += toks.millisecond_part[0]
    
    return self.time_now - total

  def column_definition_action(self, s, loc, tok):
    # print '>>> (in column_definition_action) tok = ', tok
    col = {'name':tok[0],
           'type':tok[1]
           }
    for i in xrange(2, len(tok), 2):
      if tok[i] == 'from':
        col[tok[i]] = tok[i+1]
      elif tok[i] in ['multi', 'stored']:
        col[tok[i]] = (tok[i+1] == 'true')
      elif tok[i] == 'delimiter':
        col[tok[i]] = tok[i+1]  # XXX Detect error (more than one char)
      elif tok[i] == 'index':
        col[tok[i]] = tok[i+1].upper()
      elif tok[i] == 'termvector':
        col[tok[i]] = tok[i+1].upper()
    return col

  def column_definitions_action(self, s, loc, tok):
    columns = []
    for t in tok:
      columns.append(t)
    return {'columns': columns}

  def table_option_action(self, s, loc, tok):
    # print '>>> in table_option_action, tok = ', tok
    if tok[0] == 'uid':
      return ['uid', tok[3]]
    elif tok[0] == 'source' and tok[2] == 'field':
      return ['src-data-field', tok[4]]
    elif tok[0] == 'source' and tok[2] == 'store':
      return ['src-data-store', tok[4]]
    elif tok[0] == 'delete':
      return ['delete-field', tok[3]]
    elif tok[0] == 'compress':
      return ['compress-src-data', tok[4] == 'true']

  def facet_depends_action(self, s, loc, tok):
    depends = []
    for t in tok:
      depends.append(t)
    return ('depends', depends)

  def facet_params_action(self, s, loc, tok):
    # print '>>> in facet_params_action: tok =', tok
    params = []
    for i in xrange(0, len(tok), 2):
      params.append({'name': tok[i],
                     'value': tok[i+1]
                     })
    return ('params', params)

  def facet_prop_action(self, s, loc, tok):
    # print '>>> in facet_prop_action, tok =', tok
    props = []
    for i in xrange(0, len(tok), 2):
      if tok[i] == 'depends':
        props.append(tok[i+1])
      elif tok[i] == 'dynamic':
        props.append(('dynamic', (tok[i+1] == 'true')))
      elif tok[i] == 'params':
        props.append(tok[i+1])
    return props

  def table_facet_action(self, s, loc, tok):
    '''Return a facet.

    The facet looks like this:

        {'depends': ['time'],
         'dynamic': False,
         'name': 'timeRange',
         'params': [],
         'type': 'dynamicTimeRange'
        }
    '''

    # print '>>> in table_facet_action: tok = ', tok
    facet = {}
    facet['name'] = tok[0]
    facet['type'] = tok[1]
    if tok.facet_props:
      for k,v in tok.facet_props:
        facet[k] = v
    return facet

  def show_tables_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'show_tables',
            'table_name': None
            }

  def create_table_stmt_action(self, s, loc, tok):
    # print '>>> in create_table_stmt_action: tok = ', tok
    if tok.options:             # There are table options
      options = tok.options
      for i in xrange(0, len(options), 2):
        tok.columns[options[i]] = options[i+1]

    # XXX Handle skip-field
    # tok.columns['skip-field'] = ''

    if not tok.columns.has_key('uid'):
      tok.columns['uid'] = 'id'
    if not tok.columns.has_key('src-data-field'):
      tok.columns['src-data-field'] = 'src_data'
    if not tok.columns.has_key('src-data-store'):
      tok.columns['src-data-store'] = 'lucene'
    if not tok.columns.has_key('delete-field'):
      tok.columns['delete-field'] = 'isDeleted'

    schema = {}
    schema['table'] = tok.columns
    if tok.facets:
      schema['facets'] = tok.facets[:]
    else:
      schema['facets'] = []

    return {'stmt_type':'create_table',
            'table_name':tok.table,
            'schema': schema
            }

  def drop_table_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'drop_table',
            'table_name': tok.table
            }

  def desc_table_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'desc_table',
            'table_name': tok.table
            }

  def start_table_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'start_table',
            'table_name': tok.table
            }

  def stop_table_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'stop_table',
            'table_name': tok.table
            }

  def insert_stmt_action(self, s, loc, tok):
    # print '>>> in insert_stmt_action, tok = ', tok
    columns = tok.column_list
    values = tok.value_list
    if len(columns) != len(values):
      raise ParseSyntaxException(ParseException(s, loc, 'Column list and value list do not have the same length'))
    doc = {}
    for i in xrange(len(columns)):
      doc[columns[i]] = values[i]
    return {'stmt_type': 'insert',
            'table_name': tok.table,
            'doc': doc
            }

  def load_data_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'load_data_infile',
            'table_name': tok.table,
            'file': tok.file
            }

  def update_stmt_action(self, s, loc, tok):
    columns = tok.columns
    doc = {}
    for i in xrange(0, len(columns), 3):
      doc[columns[i]] = columns[i+2]
    return {'stmt_type': 'update',
            'table_name': tok.table,
            'doc': doc,
            'uid': tok.uid
            }

  def delete_stmt_action(self, s, loc, tok):
    uids = tok.uids
    if not uids:
      uids = [tok.uid]
    return {'stmt_type': 'delete',
            'table_name': tok.table,
            'uids': uids
            }

  def truncate_table_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'truncate_table',
            'table_name': tok.table
            }

  def select_stmt_action(self, s, loc, tok):
    return {'stmt_type': 'select',
            'table_name': tok.table
            }

  def set_stmt_action(self, s, loc, tok):
    value = None
    if tok.value:
      value = tok.value
    elif tok.value_list:
      value = tok.value_list[:]
    return {'stmt_type': 'set',
            'table_name': None,
            'variable': tok.variable,
            'value': value
            }

  def alter_table_operation_action(self, s, loc, tok):
    if tok[0] == 'add' and tok[1] == 'column':
      return {'alter_type': 'alter_add_column',
              'column': tok[2]  # column_definition: {'name': 'color', 'type': 'simple'}
              }
    elif tok[0] == 'add' and tok[1] == 'facet':
      return {'alter_type': 'alter_add_facet',
              'facet': tok[2]  # table_facet: {'name': 'color', 'type': 'simple'}
              }

  def alter_table_action(self, s, loc, tok):
    operation = tok.operation
    col_or_facet = None
    if operation['alter_type'] == 'alter_add_column':
      return {'stmt_type': operation['alter_type'],
              'table_name': tok.table,
              'column': operation['column']
              }
    elif operation['alter_type'] == 'alter_add_facet':
      return {'stmt_type': operation['alter_type'],
              'table_name': tok.table,
              'facet': operation['facet']
              }

  def _build_parser(self):
    #
    # BQL Tokens
    #
    ADD = Keyword('add', caseless=True)
    AGO = Keyword('ago', caseless=True)
    ALTER = Keyword('alter', caseless=True)
    ANALYZED = Keyword('analyzed', caseless=True)
    ANALYZED_NO_NORMS = Keyword('analyzed_no_norms', caseless=True)
    CHAR = Keyword('char', caseless=True)
    COLUMN = Keyword('column', caseless=True)
    COMPRESS = Keyword('compress', caseless=True)
    CREATE = Keyword('create', caseless=True)
    DATA = Keyword('data', caseless=True)
    DATE = Keyword('date', caseless=True)
    DELETE = Keyword('delete', caseless=True)
    DELIMITER = Keyword('delimiter', caseless=True)
    DEPENDS = Keyword('depends', caseless=True)
    DESC = Keyword('desc', caseless=True)
    DESCRIBE = Keyword('describe', caseless=True)
    DOUBLE = Keyword('double', caseless=True)
    DROP = Keyword('drop', caseless=True)
    DYNAMIC = Keyword('dynamic', caseless=False)
    DYNAMICTIMERANGE = Keyword('dynamicTimeRange', caseless=False)
    FACET = Keyword('facet', caseless=True)
    FACETS = Keyword('facets', caseless=True)
    FALSE = Keyword('false', caseless=True)
    FIELD = Keyword('field', caseless=True)
    FLOAT = Keyword('float', caseless=True)
    FROM = Keyword('from', caseless=True)
    HISTOGRAM = Keyword('histogram', caseless=True)
    IN = Keyword('in', caseless=True)
    INDEX = Keyword('index', caseless=True)
    INFILE = Keyword('infile', caseless=True)
    INSERT = Keyword('insert', caseless=True)
    INT = Keyword('int', caseless=True)
    INTO = Keyword('into', caseless=True)
    LOAD = Keyword('load', caseless=True)
    LONG = Keyword('long', caseless=True)
    MULTI = Keyword('multi', caseless=True)
    NO = Keyword('no', caseless=True)
    NOT_ANALYZED = Keyword('not_analyzed', caseless=True)
    NOT_ANALYZED_NO_NORMS = Keyword('not_analyzed_no_norms', caseless=True)
    NOW = Keyword('now', caseless=True)
    PARAMS = Keyword('params', caseless=True)
    PATH = Keyword('path', caseless=True)
    RANGE = Keyword('range', caseless=True)
    SELECT = Keyword('select', caseless=True)
    SET = Keyword('set', caseless=True)
    SHORT = Keyword('short', caseless=True)
    SHOW = Keyword('show', caseless=True)
    SIMPLE = Keyword('simple', caseless=True)
    SOURCE = Keyword('source', caseless=True)
    START = Keyword('start', caseless=True)
    STOP = Keyword('stop', caseless=True)
    STORE = Keyword('store', caseless=True)
    STORES = Keyword('stores', caseless=True)
    STRING = Keyword('string', caseless=True)
    TABLE = Keyword('table', caseless=True)
    TABLES = Keyword('tables', caseless=True)
    TERMVECTOR = Keyword('termvector', caseless=True)
    TEXT = Keyword('text', caseless=True)
    TRUE = Keyword('true', caseless=True)
    TRUNCATE = Keyword('truncate', caseless=True)
    UID = Keyword('uid', caseless=True)
    UPDATE = Keyword('update', caseless=True)
    VALUES = Keyword('values', caseless=True)
    WHERE = Keyword('where', caseless=True)
    WITH = Keyword('with', caseless=True)
    WITH_OFFSETS = Keyword('with_offsets', caseless=True)
    WITH_POSITIONS = Keyword('with_positions', caseless=True)
    WITH_POSITIONS_OFFSETS = Keyword('with_positions_offsets', caseless=True)
    YES = Keyword('yes', caseless=True)

    LPAR, RPAR, COMMA, COLON, SEMICOLON = map(Suppress,'(),:;')
    ident = Word(alphas + '_', alphanums + '_-.$')
    single_column_name = (Word(alphas + '_', alphanums + '_-') | quotedString)
    column_name = single_column_name + Optional('.' + single_column_name)
    table_name = Word(alphas + '_', alphanums + '_-.')
    facet_name = column_name.copy()

    integer = Word(nums).setParseAction(lambda t: int(t[0]))
    real = Combine(Word(nums) + '.' + Word(nums)).setParseAction(lambda t: float(t[0]))
    quotedString.setParseAction(removeQuotes)
    
    # Time expression
    CL = CaselessLiteral
    week = Combine(CL('week') + Optional(CL('s')))
    day = Combine(CL('day') + Optional(CL('s')))
    hour = Combine(CL('hour') + Optional(CL('s')))
    minute = Combine((CL('minute') | CL('min')) + Optional(CL('s')))
    second = Combine((CL('second') | CL('sec')) + Optional(CL('s')))
    millisecond = Combine((CL('millisecond') | CL('msec')) + Optional(CL('s')))
    
    time_week_part = (integer + week).setResultsName('week_part')
    time_day_part = (integer + day).setResultsName('day_part')
    time_hour_part = (integer + hour).setResultsName('hour_part')
    time_minute_part = (integer + minute).setResultsName('minute_part')
    time_second_part = (integer + second).setResultsName('second_part')
    time_millisecond_part = (integer + millisecond).setResultsName('millisecond_part')
    
    time_span = (Optional(time_week_part) +
                 Optional(time_day_part) +
                 Optional(time_hour_part) +
                 Optional(time_minute_part) +
                 Optional(time_second_part) +
                 Optional(time_millisecond_part)).setParseAction(self.convert_time_span)
    
    date_time_string = Regex(DATE_TIME).setResultsName('date_time_regex').setParseAction(self.convert_time)
    
    time_expr = ((time_span + AGO)
                 | date_time_string
                 | NOW.setParseAction(self.convert_time))

    data_type = (UID | INT | SHORT | CHAR | LONG | FLOAT | DOUBLE | STRING | DATE | TEXT)

    column_prop = (MULTI + (TRUE | FALSE) + Optional(DELIMITER + quotedString)
                   | STORE + (TRUE | FALSE)
                   | INDEX + (NO | ANALYZED | NOT_ANALYZED | ANALYZED_NO_NORMS | NOT_ANALYZED_NO_NORMS)
                   | TERMVECTOR + (NO | WITH_OFFSETS | WITH_POSITIONS | WITH_POSITIONS_OFFSETS | YES)
                   )

    column_definition = (column_name + data_type +
                         Optional(FROM + column_name) +
                         ZeroOrMore(column_prop)
                         ).setParseAction(self.column_definition_action)

    column_definitions = delimitedList(column_definition).setParseAction(self.column_definitions_action)

    table_option = (UID + FIELD + '=' + column_name
                    | SOURCE + DATA + FIELD + '=' + column_name
                    | SOURCE + DATA + STORE + '=' + quotedString
                    | DELETE + FIELD + '=' + column_name
                    | COMPRESS + SOURCE + DATA + '=' + (TRUE | FALSE)
                    ).setParseAction(self.table_option_action)

    table_options = delimitedList(table_option)

    facet_type = (SIMPLE
                  | MULTI
                  | PATH
                  | RANGE
                  | HISTOGRAM
                  | DYNAMICTIMERANGE
                  )

    facet_depends = (facet_name
                     | LPAR + delimitedList(facet_name) + RPAR
                     ).setParseAction(self.facet_depends_action)

    facet_param = (quotedString + COLON + quotedString)

    facet_params = (LPAR + delimitedList(facet_param) + RPAR
                    ).setParseAction(self.facet_params_action)

    facet_prop = (DEPENDS + facet_depends
                  | DYNAMIC + (TRUE | FALSE)
                  | PARAMS + facet_params
                  ).setParseAction(self.facet_prop_action)

    table_facet = (column_name + facet_type +
                   ZeroOrMore(facet_prop).setResultsName('facet_props')
                   ).setParseAction(self.table_facet_action)

    table_facets = delimitedList(table_facet)

    show_tables_stmt = (SHOW + (TABLES | STORES)
                        ).setParseAction(self.show_tables_stmt_action)

    create_table_stmt = (CREATE + TABLE + table_name.setResultsName('table') +
                         LPAR + column_definitions.setResultsName('columns') + RPAR +
                         Optional(table_options.setResultsName('options')) +
                         Optional(WITH + FACETS +
                                  LPAR + table_facets.setResultsName('facets') + RPAR)
                         ).setParseAction(self.create_table_stmt_action)

    drop_table_stmt = (DROP + TABLE +
                       table_name.setResultsName('table')
                       ).setParseAction(self.drop_table_stmt_action)

    desc_table_stmt = ((DESC | DESCRIBE) +
                       table_name.setResultsName('table')
                       ).setParseAction(self.desc_table_stmt_action)

    start_table_stmt = (START +
                        table_name.setResultsName('table')
                        ).setParseAction(self.start_table_stmt_action)

    stop_table_stmt = (STOP +
                        table_name.setResultsName('table')
                        ).setParseAction(self.stop_table_stmt_action)

    column_list = delimitedList(column_name)

    number = (real | integer)       # Put real before integer to avoid ambiguity
    numeric = (time_expr | number)

    value = (numeric | quotedString)
    value_list = LPAR + delimitedList(value) + RPAR

    insert_stmt = (INSERT + INTO +
                   table_name.setResultsName('table') +
                   LPAR + column_list.setResultsName('column_list') + RPAR +
                   VALUES +
                   value_list.setResultsName('value_list')
                   ).setParseAction(self.insert_stmt_action)

    load_data_stmt = (LOAD + DATA + INFILE +
                      quotedString.setResultsName('file') +
                      INTO + TABLE +
                      table_name.setResultsName('table')
                      ).setParseAction(self.load_data_stmt_action)

    update_column = column_name + '=' + value
    update_columns = delimitedList(update_column)

    update_stmt = (UPDATE +
                   table_name.setResultsName('table') +
                   SET + update_columns.setResultsName('columns') +
                   WHERE + UID + '=' + integer.setResultsName('uid')
                   ).setParseAction(self.update_stmt_action)

    uid_list = delimitedList(integer)

    delete_stmt = (DELETE + FROM +
                   table_name.setResultsName('table') +
                   WHERE + UID +
                   ('=' + integer.setResultsName('uid')
                    | IN + LPAR + uid_list.setResultsName('uids') + RPAR
                    )
                   ).setParseAction(self.delete_stmt_action)

    truncate_table_stmt = (TRUNCATE + TABLE +
                           table_name.setResultsName('table')
                           ).setParseAction(self.truncate_table_stmt_action)

    select_stmt = (SELECT +
                   ('*' | column_list) +
                   FROM + table_name.setResultsName('table') + restOfLine
                   ).setParseAction(self.select_stmt_action)

    set_stmt = (SET +
                ident.setResultsName("variable") +
                (value.setResultsName("value") | value_list.setResultsName('value_list'))
                ).setParseAction(self.set_stmt_action)

    add_column_definition = (ADD + COLUMN +
                             column_definition)

    add_facet_definition = (ADD + FACET +
                            table_facet)

    alter_table_operation = (add_column_definition
                             | add_facet_definition
                             # | alter_column_definition
                             # | drop_column_definition
                             )    

    alter_table_stmt = (ALTER + TABLE +
                        table_name.setResultsName('table') +
                        alter_table_operation.setResultsName('operation').setParseAction(self.alter_table_operation_action)
                        ).setParseAction(self.alter_table_action)

    BQLstmt = (show_tables_stmt
               | create_table_stmt
               | drop_table_stmt
               | desc_table_stmt
               | start_table_stmt
               | stop_table_stmt
               | insert_stmt
               | load_data_stmt
               | update_stmt
               | delete_stmt
               | truncate_table_stmt
               | select_stmt
               | set_stmt
               | alter_table_stmt
               ) + Optional(SEMICOLON) + stringEnd

    sql_comment = '--' + restOfLine
    BQLstmt.ignore(sql_comment)
    return BQLstmt

class SinClient:
  '''Sin Client.'''

  def __init__(self, host='localhost', port=8666, max_col_width=100):
    self.host = host
    self.port = port
    self.max_col_width = max_col_width
    self.stores = None
    self.store_map = {}
    self.cookie_jar = cookielib.CookieJar()
    self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
    self.parser = BQLParser()

  def get_stores_info(self):
    '''Get info of all stores.'''
    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    urlReq = urllib2.Request(baseurl + '/stores')
    stores = self.opener.open(urlReq).read()
    self.stores = json.loads(stores)
    for store in self.stores:
      self.store_map[store.get('name')] = store

  def login(self, username, password):
    url = 'http://%s:%s/login_api' % (self.host, self.port)
    res = self.opener.open(url, json.dumps({'username': username, 'password': password}))
    obj = json.loads(res.read())
    if not obj.get('ok'):
      raise Exception(obj.get('msg', 'Login failed'))

    self.get_stores_info()
    return True

  def logout(self):
    url = 'http://%s:%s/logout_api' % (self.host, self.port)
    res = self.opener.open(url)
    obj = json.loads(res.read())
    if not obj.get('ok'):
      raise Exception(obj.get('msg', 'Logout failed'))
    return True

  def show_stores(self):
    '''Execute SHOW STORES command.'''

    self.get_stores_info()
    if len(self.stores) == 0:
      sys.stdout.write('No table is found.\n')
      return
    keys = ['name', 'description']
    max_lens = None

    def get_max_lens(keys):
      max_lens = {}
      for key in keys:
        max_lens[key] = len(key)
      for store in self.stores:
        for key in keys:
          tmp_len = len(store.get(key))
          if tmp_len > max_lens[key]:
            max_lens[key] = tmp_len
      return max_lens

    def print_line(keys, max_lens, char='-', sep_char='+'):
      sys.stdout.write(sep_char)
      for key in keys:
        sys.stdout.write(char * (max_lens[key] + 2) + sep_char)
      sys.stdout.write('\n')

    def print_header(keys, max_lens):
      print_line(keys, max_lens, '-', '+')
      sys.stdout.write('|')
      for key in keys:
        sys.stdout.write(' %s%s |' % (key, ' ' * (max_lens[key] - len(key))))
      sys.stdout.write('\n')
      print_line(keys, max_lens, '-', '+')

    def print_footer(keys, max_lens):
      print_line(keys, max_lens, '-', '+')

    max_lens = get_max_lens(keys)
    print_header(keys, max_lens)
    for store in self.stores:
      sys.stdout.write('|')
      for key in keys:
        val = store.get(key)
        sys.stdout.write(' %s%s |' % (val, ' ' * (max_lens[key] - len(val))))
      sys.stdout.write('\n')
    print_footer(keys, max_lens)

  def open_store(self, name, api_key):
    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl,'open-store',name)
    urlReq = urllib2.Request(url)
    self.opener.addheaders = [('X-Sin-Api-Key', api_key)]
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    
    if not jsonObj['ok']:
      errorMsg = 'error: %s' % jsonObj.get('error','unknown error')
      raise Exception(errorMsg)
    
    brokerPort = jsonObj['broker_port']
    senseiPort = jsonObj['sensei_port']
    storeId = jsonObj['id']
    storeConfig = jsonObj.get('config')
    storeCreated = jsonObj['created']
    storeStatus = jsonObj['status']
    description = jsonObj.get('description',None)
    status = jsonObj['status_display']
    
    senseiClient = SenseiClient(self.host, brokerPort)
    sindex = Sindex(storeId,
                    name,
                    api_key,
                    description,
                    storeCreated,
                    baseurl,
                    storeConfig,
                    senseiClient,status,
                    self.cookie_jar)
    while not sindex.available():
      time.sleep(0.5)
    
    return sindex

  def start_store(self, name, config_id):
    '''Start a store.'''

    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s/%d' % (baseurl,'start-store', name, config_id)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      errorMsg = 'error: %s' % jsonObj.get('error','unknown error')
      raise Exception(errorMsg)
    return jsonObj

  def stop_store(self, name):
    '''Stop a store.'''

    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl,'stop-store', name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      errorMsg = 'error: %s' % jsonObj.get('error','unknown error')
      raise Exception(errorMsg)
    return jsonObj

  def add_doc(self, store_name, doc):
    '''Add a document to a store.'''

    return self.add_docs(store_name, [doc])

  def add_docs(self, store_name, docs):
    '''Add a list of documents to a store.'''
    
    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl, 'add-docs', store_name)
    params = urllib.urlencode({'docs': json.dumps(docs)})
    urlReq = urllib2.Request(url, params)
    res = self.opener.open(urlReq)

    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('numPosted', 0)

  def update_doc(self, store_name, doc):
    '''Update a document in a store.'''

    if not doc:
      raise Exception('No doc is supplied.')
    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl, 'update-doc', store_name)
    params = urllib.urlencode({'doc': json.dumps(doc)})
    urlReq = urllib2.Request(url, params)
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('numPosted',0)

  def delete_docs(self, store_name, uids):
    '''Delete a list of documents from a store.'''
    
    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl,'delete-docs', store_name)
    params = urllib.urlencode({'ids': uids})
    urlReq = urllib2.Request(url, params)
    res = self.opener.open(urlReq)

    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      raise Exception('error: %s' % jsonObj.get('error','unknown error'))
    return jsonObj.get('numDeleted', 0)

  def do_query(self, store_name, bql_stmt, var_map={}):
    '''Execute a SELECT query.'''

    store = self.store_map.get(store_name)
    client = SenseiClient(store['broker_host'], store['broker_port'])
    return client.doQuery(bql_stmt, var_map=var_map)

  def compile(self, bql_stmt):
    '''Compile a BQL statement.'''

    tokens = self.parser.parse(bql_stmt)
    if tokens:
      logger.debug('tokens: %s' % tokens)
    else:
      logger.debug('Empty tokens')
    return tokens

  def new_store(self, name, rep=1, parts=2, description=''):
    '''Create a new store.'''

    baseurl = 'http://%s:%d/%s' % (self.host,self.port,'store')
    url = '%s/%s/%s' % (baseurl,'new-store',name)
    params = urllib.urlencode(dict(replica=rep,partitions=parts,desc=description))
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq, params)
    jsonObj = json.loads(res.read())
    return jsonObj

  def get_store_config(self, store_name):
    '''Get the current config for a store.'''

    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl, 'configs', store_name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    if len(jsonObj) == 1:
      # print '>>> one config: ', jsonObj[0]
      return jsonObj[0]
    for config in jsonObj:
      if config['active']:
        print '>>> found active config: ', config
        return config

  def update_store_schema(self, store_name, config_id, schema):
    '''Update the schema of a store.'''

    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s/%d' % (baseurl, store_name, 'update-schema', config_id)
    params = {}
    params['schema'] = json.dumps(schema)
    res = self.opener.open(url, urllib.urlencode(params))
    jsonObj = json.loads(res.read())
    return jsonObj

  def store_exists(self, store_name):
    '''Get store existence info.'''

    baseurl = 'http://%s:%d/%s' % (self.host,self.port,'store')
    url = '%s/%s/%s' % (baseurl,'exists', store_name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = dict(json.loads(res.read()))
    return jsonObj['exists']
    
  def delete_store(self, store_name):
    '''Delete a store.'''

    baseurl = 'http://%s:%d/%s' % (self.host,self.port,'store')
    url = '%s/%s/%s' % (baseurl,'delete-store', store_name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = dict(json.loads(res.read()))
    if not jsonObj['ok']:
      errorMsg = 'error: %s' % jsonObj.get('msg','unknown error')
      raise Exception(errorMsg)

  def purge_store(self, store_name):
    '''Purge a store.

    This is similar to TRUNCATE TABLE in SQL.

    '''

    baseurl = 'http://%s:%d/%s' % (self.host, self.port, 'store')
    url = '%s/%s/%s' % (baseurl, 'purge-store', store_name)
    urlReq = urllib2.Request(url)
    res = self.opener.open(urlReq)
    jsonObj = json.loads(res.read())
    if not jsonObj['ok']:
      errorMsg = 'error: %s' % jsonObj.get('msg','unknown error')
      raise Exception(errorMsg)

def main(argv):

  def help():
    print '''\
help                              Show instructions
alter table ...                   Alter a table (column or facet)
create table <table_name> ...     Create a table
delete from <table_name> ...      Delete a document from a table
desc <table_name>                 Describe table 
drop table <table_name>           Drop a table
insert into <table_name> ...      Insert a document into a table
load data infile <file> into ...  Load documents (in JSON format) from a file
                                  into a table
select ... from <table_name> ...  Execute a BQL SELECT statement
set var value                     Assign a value to a variable     
show tables                       Show all tables
start <table_name>                Start a table
stop <table_name>                 Stop a table
truncate table <table_name>       Purge all data from a table
update <table_name> ...           Update a document in a table
exit                              Exit
'''

  def cleanup():
    ''' clean up when the user exit the command line
    '''

  def getStoreName(stmt):
    if stmt.startswith('use '):
      args = stmt.split()
      return args[1]
    else:
      return ''
    
  def testStore(store, api_key):
    try:
        sinClient_test = SinClient()
        sinClient_test.open_store(store, api_key)
        return True
    except:
      return False

  def execute_bql(stmt):
    stmt_info = my_client.compile(stmt)[0]
    stmt_type = stmt_info['stmt_type']
    store_name = stmt_info['table_name']
    res = None

    if stmt_type == 'show_tables':
      #
      # SHOW TABLES
      #
      my_client.show_stores()
    elif stmt_type == 'create_table':
      #
      # CREATE TABLE
      #
      my_client.new_store(store_name, description='testing ' + store_name)
      config = my_client.get_store_config(store_name)
      my_client.update_store_schema(store_name, config['id'], stmt_info['schema'])
      my_client.get_stores_info()
    elif stmt_type == 'drop_table':
      #
      # DROP TABLE
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      if store['status_display'] == 'Running':
        print 'Store %s is currently running.  Please stop it first.' % store_name
        return
      my_client.delete_store(store_name)
      my_client.get_stores_info()
    elif stmt_type == 'desc_table':
      #
      # DESC TABLE
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      client = SenseiClient(store['broker_host'], store['broker_port'])
      sysinfo = client.get_sysinfo()
      sysinfo.display()
    elif stmt_type == 'start_table':
      #
      # START table
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      config = my_client.get_store_config(store_name)
      print 'Starting table %s...' % store_name
      my_client.start_store(store_name, config['id'])
      my_client.get_stores_info()
    elif stmt_type == 'stop_table':
      #
      # STOP table
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      my_client.stop_store(store_name)
      my_client.get_stores_info()
    elif stmt_type in ['insert', 'update', 'delete', 'select']:
      #
      # INSERT, UPDATE, DELETE, SELECT
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      elif store['status_display'] != 'Running':
        print 'Store %s is not started!' % store_name
        return
      if stmt_type == 'insert':
        res = my_client.add_doc(store_name, stmt_info['doc'])
      elif stmt_type == 'update':
        schema = json.loads(store['current_config']['schema'])
        uid_col = schema['table']['uid']
        doc = stmt_info['doc']
        doc[uid_col] = stmt_info['uid']
        res = my_client.update_doc(store_name, doc)
      elif stmt_type == 'delete':
        res = my_client.delete_docs(store_name, stmt_info['uids'])
      elif stmt_type == 'select':
        res = my_client.do_query(store_name, stmt, var_map)
        error = res.error
        if error:
          err_code = error.get('code')
          err_msg = error.get('msg')
          if err_code == 499:
            err_match = re.match(r'^\[line:(\d+), col:(\d+)\].*', err_msg)
            print '%s^' % (' ' * (5 + int(err_match.group(2))))
            print err_msg
          else:
            print 'Unknown error happened!'
        else:
          select_list = res.jsonMap.get('select_list') or ['*']
          res.display(columns=select_list, max_col_width=my_client.max_col_width)
    elif stmt_type == 'load_data_infile':
      #
      # LOAD DATA INFILE
      #
      file_name = stmt_info['file']
      try:
        data_file = open(file_name)
        for line in data_file:
          doc = json.loads(line)
          res = my_client.add_doc(store_name, doc)
      except Exception as err:
        print 'Error reading file %s!' % file_name
    elif stmt_type == 'truncate_table':
      #
      # TRUNCATE TABLE
      #
      store = my_client.store_map.get(store_name)
      if not store:
        print 'Store %s does not exist!' % store_name
        return
      elif store['status_display'] != 'Running':
        print 'Store %s is not started!' % store_name
        return
      my_client.purge_store(store_name)
    elif stmt_type == 'set':
      #
      # SET variable
      #
      var_map[stmt_info['variable']] = stmt_info['value']
    elif stmt_type == 'alter_add_column':
      #
      # ALTER ADD COLUMN
      #
      print '>>> stmt_info = ', stmt_info
      store = my_client.store_map.get(store_name)
      current_schema = json.loads(store['current_config']['schema'])
      print '>>> current_schema =', current_schema
      col_name = stmt_info['column']['name']
      current_columns = current_schema['table']['columns']
      for col in current_columns:
        if col['name'] == col_name:
          print 'Column %s already exists!' % col_name
          return
      current_columns.append(stmt_info['column'])
      print '>>> new schema = ', current_schema
      config = my_client.get_store_config(store_name)
      my_client.update_store_schema(store_name, config['id'], current_schema)
      my_client.get_stores_info()
    elif stmt_type == 'alter_add_facet':
      #
      # ALTER ADD FACET
      #
      print '>>> stmt_info = ', stmt_info
      store = my_client.store_map.get(store_name)
      current_schema = json.loads(store['current_config']['schema'])
      print '>>> current_schema =', current_schema
      facet_name = stmt_info['facet']['name']
      current_facets = current_schema['facets']
      for facet in current_facets:
        if facet['name'] == facet_name:
          print 'Facet %s already exists!' % facet_name
          return
      current_facets.append(stmt_info['facet'])
      print '>>> new schema = ', current_schema
      config = my_client.get_store_config(store_name)
      my_client.update_store_schema(store_name, config['id'], current_schema)
      my_client.get_stores_info()
    else:
      print 'Unrecognized command.'    

  print 'Welcome to Dataganic Shell (Version 0.2)!'

  usage = 'Usage: %prog [options]'
  parser = OptionParser(usage=usage)
  parser.add_option('-a', '--add-docs', dest='store',
                    help='Add docs to a store based on standard input')
  parser.add_option('-n', '--host', dest='host',
                    default='localhost', help='Host name of Sin server')
  parser.add_option('-o', '--port', dest='port',
                    default=8666, help='Port of Sin server')
  parser.add_option('-p', '--password', dest='password',
                    help='Sin user password')
  parser.add_option('-u', '--user', dest='user',
                    help='Sin user name (login id)')
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                    default=False, help='Turn on verbose mode')
  parser.add_option('-w', '--column-width', dest='max_col_width',
                    default=100, help='Set the max column width')

  (options, args) = parser.parse_args()
  if options.password == None:
    options.password = getpass.getpass()

  logger.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)d - %(message)s')
  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)

  my_client = SinClient(options.host,
                        int(options.port),
                        max_col_width=int(options.max_col_width))

  my_client.login(options.user, options.password)

  if options.store:
    # Add docs based on standard input
    store_name = options.store
    while 1:
      try:
        line = sys.stdin.readline()
      except KeyboardInterrupt:
        break
      doc = json.loads(line)
      try:
        res = my_client.add_doc(store_name, doc)
      except Exception as e:
        logging.exception(e);
    return

  var_map = {}

  import readline
  store = ''
  readline.parse_and_bind('tab: complete')
  print 'Type "help" for help, "exit" to quit.'

  while 1:
    try:
      stmt = raw_input('bql> ')
      words = re.split(r'[\s,]+', stmt.strip())
      command = len(words) > 0 and words[0].lower() or None

      if len(words) == 1 and command == 'exit':
        cleanup()
        break;
      elif command == 'help':
        help()
      elif not command:
        # Empty input
        pass
      else:
        execute_bql(stmt)
    except EOFError:
      print 'EOF error'
      break
    except Exception as err:
      print err

if __name__ == '__main__':
    main(sys.argv)

'''
Tests:

create table t1 (name string, memberId int) uid field = id with facets (name simple, memberId simple)
start t1
desc t1
insert into t1 (id, name, memberId) values (1, 'Baoqiu Cui', 111)
insert into t1 (id, name, memberId) values (2, 'Kyle Cui', 222)
insert into t1 (id, name, memberId) values (3, 'Kelly Cui', 333)
delete from t1 where uid = 1
delete from t1 where uid in (1,2,3)
drop table t1
load data infile '/Users/bcui/Projects/sin/client/python/test/data/load_data_test.json' into table t1
select _uid, name, memberId from t1
truncate table t1

For tweet:

create table tweet (name string, screen_name string, user_id long, time long, contents text index analyzed termvector no) uid field = id_str with facets(name simple, user_id simple, screen_name simple, time range, timeRange dynamicTimeRange depends time params ("range":"000000100", "range":"000010000", "range":"001000000"))

create table tweet (
  name        string,
  screen_name string,
  user_id     long,
  time        long,
  contents    text index analyzed termvector no
)
uid field = id_str
with facets (
  name        simple,
  user_id     simple,
  screen_name simple,
  time        range,
  timeRange   dynamicTimeRange
              depends time
              dynamic true
              params ("range":"000000100", "range":"000010000", "range":"001000000")
)

'''
