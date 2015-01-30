#!/usr/bin/env python

'''
Read tweets from standard input, apply Sensei filtering on each of them,
and print out the filtered Sensei documents.

DDL:

create table tweet (
  name        string,
  screen_name string,
  user_id     long,
  time        long,
  hashtags    string,
  mentions    string,
  contents    text index analyzed termvector no
)
uid field = id_str
with facets (
  name        simple,
  user_id     simple,
  screen_name simple,
  time        range,
  hashtags    multi,
  mentions    multi,
  timeRange   dynamicTimeRange
              depends time
              params ("range":"000000100",
                      "range":"000010000",
                      "range":"001000000")
)

A tweet looks like this:

------------------------------------------------------------------------
{
    "in_reply_to_user_id_str":null,
    "geo":null,
    "in_reply_to_status_id":null,
    "text":"RT @MileHighReport: Never, EVER, count a John Elway-led #Broncos team out of it.",
    "truncated":false,
    "entities":{
        "urls":[],
        "hashtags":[{"text":"Broncos","indices":[56,64]}],
        "user_mentions":[{"indices":[3,18],"screen_name":"MileHighReport","name":"MileHighReport","id_str":"14583608","id":14583608}]
    },
    "in_reply_to_screen_name":null,
    "place":null,
    "retweeted":false,
    "source":"web",
    "retweeted_status":{"in_reply_to_user_id_str":null,"geo":null,"in_reply_to_status_id":null,"text":"Never, EVER, count a John Elway-led #Broncos team out of it.","truncated":false,"entities":{"urls":[],"hashtags":[{"text":"Broncos","indices":[36,44]}],"user_mentions":[]},"in_reply_to_screen_name":null,"place":null,"retweeted":false,"source":"\u003Ca href=\"http:\/\/www.tweetdeck.com\" rel=\"nofollow\"\u003ETweetDeck\u003C\/a\u003E","coordinates":null,"in_reply_to_user_id":null,"id_str":"181782612866629633","contributors":null,"in_reply_to_status_id_str":null,"user":{"profile_sidebar_border_color":"BDDCAD","url":"http:\/\/www.milehighreport.com","show_all_inline_media":false,"listed_count":491,"follow_request_sent":null,"verified":false,"is_translator":false,"profile_use_background_image":true,"default_profile":false,"lang":"en","statuses_count":27435,"profile_text_color":"333333","description":"Denver Broncos Blogger Extraordinaire","location":"\u00dcT: 41.413427,-82.176612","profile_background_image_url":"http:\/\/a0.twimg.com\/profile_background_images\/16619431\/MileHighReport.jpg","notifications":null,"profile_background_image_url_https":"https:\/\/si0.twimg.com\/profile_background_images\/16619431\/MileHighReport.jpg","time_zone":"Eastern Time (US & Canada)","profile_link_color":"0084B4","following":null,"profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/505041022\/twitterProfilePhoto_normal.jpg","screen_name":"MileHighReport","default_profile_image":false,"profile_background_color":"9AE4E8","followers_count":9268,"protected":false,"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/505041022\/twitterProfilePhoto_normal.jpg","id_str":"14583608","profile_background_tile":true,"favourites_count":0,"name":"MileHighReport","contributors_enabled":false,"geo_enabled":false,"friends_count":548,"profile_sidebar_fill_color":"DDFFCC","id":14583608,"utc_offset":-18000,"created_at":"Tue Apr 29 11:56:24 +0000 2008"},"retweet_count":64,"favorited":false,"id":181782612866629633,"created_at":"Mon Mar 19 16:42:06 +0000 2012"},
    "coordinates":null,
    "in_reply_to_user_id":null,
    "id_str":"181792237695414272",
    "contributors":null,
    "in_reply_to_status_id_str":null,
    "user":{
        "profile_sidebar_border_color":"C0DEED",
        "url":null,
        "show_all_inline_media":false,
        "listed_count":0,
        "follow_request_sent":null,
        "verified":false,
        "is_translator":false,
        "profile_use_background_image":true,
        "default_profile":true,
        "lang":"en",
        "statuses_count":11,
        "profile_text_color":"333333",
        "description":null,
        "location":null,
        "profile_background_image_url":"http:\/\/a0.twimg.com\/images\/themes\/theme1\/bg.png",
        "notifications":null,
        "profile_background_image_url_https":"https:\/\/si0.twimg.com\/images\/themes\/theme1\/bg.png",
        "time_zone":null,
        "profile_link_color":"0084B4",
        "following":null,
        "profile_image_url_https":"https:\/\/si0.twimg.com\/sticky\/default_profile_images\/default_profile_2_normal.png",
        "screen_name":"markthom07",
        "default_profile_image":true,
        "profile_background_color":"C0DEED",
        "followers_count":1,
        "protected":false,
        "profile_image_url":"http:\/\/a0.twimg.com\/sticky\/default_profile_images\/default_profile_2_normal.png",
        "id_str":"80321579",
        "profile_background_tile":false,
        "favourites_count":1,
        "name":"mark thompson",
        "contributors_enabled":false,
        "geo_enabled":false,
        "friends_count":18,
        "profile_sidebar_fill_color":"DDEEF6",
        "id":80321579,
        "utc_offset":null,
        "created_at":"Tue Oct 06 14:57:30 +0000 2009"
    },
    "retweet_count":64,
    "favorited":false,
    "id":181792237695414272,
    "created_at":"Mon Mar 19 17:20:21 +0000 2012"
}
------------------------------------------------------------------------

'''

import json
import sys
import time
from dateutil.parser import *

while True:
  try:
    line = sys.stdin.readline()
    input_json = json.loads(line)
    if (not input_json.has_key('user') or
        not input_json.has_key('id_str')):
      continue
    output_json = {}
    output_json['id_str'] = input_json['id_str']
    created_time = input_json['created_at']
    if created_time:
      try:
        # timestamp = long(time.mktime(parse(created_time).timetuple()))
        # output_json['time'] = timestamp * 1000
        output_json['time'] = int(time.time() * 1000)
      except Exception as err:
        # Ignore this line
        pass
    output_json['contents'] = input_json['text']
    if input_json.has_key('user'):
      user = input_json['user']
      output_json['name'] = user['name']
      output_json['user_id'] = user['id']
      output_json['screen_name'] = user['screen_name']
    if input_json.has_key('entities'):
      entities = input_json['entities']
      if entities.has_key('hashtags'):
        hashtags = ','.join(ht['text'] for ht in entities['hashtags'])
        if len(hashtags) > 0:
          output_json['hashtags'] = hashtags
      if entities.has_key('user_mentions'):
        mentions = ','.join(ht['screen_name'] for ht in entities['user_mentions'])
        if len(mentions) > 0:
          output_json['mentions'] = mentions
    print json.dumps(output_json)
  
  except KeyboardInterrupt:
    break
