#
# Copyright 2014 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
## -*- coding: utf-8 -*-

import os
import cherrypy
import requests
import json
from random import choice
from mako.template import Template
from mako.lookup import TemplateLookup


class InsightsService:
    """Wrapper on the Personality Insights service"""

    def __init__(self, vcapServices):
        """
        Construct an instance. Fetches service parameters from VCAP_SERVICES
        runtime variable for Bluemix, or it defaults to local URLs.
        """

        # Local variables
        self.url = "<url>"
        self.username = "<username>"
        self.password = "<password>"

        if vcapServices is not None:
            print("Parsing VCAP_SERVICES")
            services = json.loads(vcapServices)
            svcName = "concept_insights"# "personality_insights"
            if svcName in services:
                print("insights service found!")
                svc = services[svcName][0]["credentials"]
                self.url = svc["url"]
                self.username = svc["username"]
                self.password = svc["password"]
            else:
                print("ERROR: The Personality Insights service was not found")

    def getProfile(self, text):
        """Returns the profile by doing a POST to /v2/profile with text"""

        if self.url is None:
            raise Exception("No Personality Insights service is bound to this app")
        response = requests.post(self.url + "/v2/graphs/wikipedia/en-20120601/annotate_text",            # profile",
                          auth=(self.username, self.password),    # /graphs/wikipedia/en-20120601/annotate_text
                           headers = {"content-type": "text/plain"},
                           data=text
                          )
        try:
            return json.loads(response.text)
        except:
            raise Exception("Error processing the request, HTTP: %d" % response.status_code)


class DemoService(object):
    """
    REST service/app. Since we just have 1 GET and 1 POST URLs,
    there is not even need to look at paths in the request.
    This class implements the handler API for cherrypy library.
    """
    exposed = True

    def __init__(self, service):
        self.service = service
        self.defaultContent = None
        try:
            contentFile = open("public/text/en.txt", "r")
            self.defaultContent = contentFile.read()
        except Exception as e:
            print "ERROR: couldn't read mobidick.txt: %s" % e
        finally:
            contentFile.close()

    def GET(self):
        """Shows the default page with sample text content"""

        return lookup.get_template("index.html").render(content=self.defaultContent)


    def POST(self, text=None):
        """
        Send 'text' to the Personality Insights API
        and return the response.
        """
        try:
            profileJson = self.service.getProfile(text)
            interesting = list({a["concept"]["label"] for a in profileJson["annotations"] 
                                                                     if a["score"] > 0.615})
        
            titles = []

            for i in range(100):
                word1 = choice(interesting)
                word2 = choice(interesting)
                combo = choice([1,2,3,4,5,6])
                if combo < 3:
                    # the ####### of word 1 and word2
                    prefixes = ["The exciting possibilities of ", 
                                "The fascinating relationship between ",
                                "The cause of "]
                    titles.append( choice(prefixes) + word1  + " and " + word2)
                if combo < 6:
                    # word1 and word2: the 
                    endings = [": the pivotal relationship",
                               ": theory and practice",
                               ": the core of the issue"]
                    titles.append(word1 + " and " + word2 + choice(endings))
                
                if combo == 6:
                    titles.append(word1 + " and " + word2)


            profileJson["titles"] = titles # ["duck", "goose"]  # [get_title(interesting) for a in range(100)]
    
            return json.dumps(profileJson)
        except Exception as e:
            print "ERROR: %s" % e
            return str(e)

            
 

if __name__ == '__main__':
    lookup = TemplateLookup(directories=["templates"])

    # Get host/port from the Bluemix environment, or default to local
    HOST_NAME = os.getenv("VCAP_APP_HOST", "127.0.0.1")
    PORT_NUMBER = int(os.getenv("VCAP_APP_PORT", "3000"))
    cherrypy.config.update({
        "server.socket_host": HOST_NAME,
        "server.socket_port": PORT_NUMBER,
    })

    # Configure 2 paths: "public" for all JS/CSS content, and everything
    # else in "/" handled by the DemoService
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.response_headers.on": True,
            "tools.staticdir.root": os.path.abspath(os.getcwd())
        },
        "/public": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": "./public"
        }
    }

    # Create the Personality Insights Wrapper
    insights = InsightsService(os.getenv("VCAP_SERVICES"))

    # Start the server
    print("Listening on %s:%d" % (HOST_NAME, PORT_NUMBER))
    cherrypy.quickstart(DemoService(insights), "/", config=conf)
