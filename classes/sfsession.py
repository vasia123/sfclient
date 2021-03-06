#!/usr/bin/python
# coding=utf-8

'''
    Shakes & Fidget command line client

    by Chocokiko

    Session Object

'''

import random
import time
import requests

from legacy.sfserverglobals import ACT
from legacy.sfglobals import CNT

from legacy.sflegacy import on_stage

from classes.sfexceptions import RequestFailedException


class Session(object):
    '''
        Session object to handle request stuff
    '''
    def __init__(self, logger):
        '''
            Constructor to Session object
        '''
        # TODO: Check if needed?
        self.param_poll_tunnel_url = ""
        self.param_fail_tries = 1

        self.poll_lock = False
        self.send_lock = False
        self.fight_lock = False
        self.mp_api_user_id = 'notset'
        self.mp_api_user_token = 'notset'
        self.last_act = None

        self.server = 's31.sfgame.de'

        self.baseuri = 'http://s31.sfgame.de/request.php'
        self.loginparams = '?req=&random=%%2&rnd=%s%s'

        self.req_format = '%s%%3B%s%%3bv1.70'
        self.rnd_format = '%s%s'

        self.session_id = '00000000000000000000000000000000'
        self.user = 'chocokiko'
        self.pwdmd5 = 'c33def595b633a53fbb6a3987ab54a05'
        random.seed()

        self.log = logger

    def login(self):
        '''
            login to server

            TODO: refactor to use sendAction()
        '''
        action = '002'

        req_string = self.req_format % (
            self.session_id + action + self.user, self.pwdmd5
        )

        random_string = '%2'
        # TODO: rework random number generation
        rnd_string = self.rnd_format % (
            random.randint(0, 9999999999),
            int(time.time() * 1000)
        )

        payload = {
            'req': req_string,
            'random': random_string,
            'rnd': rnd_string
        }

        resp = requests.get(self.baseuri, params=payload)

        return resp.text.split('/')

    def send_action(self, action, actor, *params):
        '''
            Send formatted request to server
        '''
        if action == ACT['GET_CHAT_HISTORY']:
            if not on_stage(CNT['IF_LOGOUT'], actor):
                return
            if (self.param_poll_tunnel_url != "") and self.poll_lock:
                return
            elif self.poll_lock or self.send_lock or self.fight_lock:
                return action

        elif self.send_lock:
            if (action not in (
                    ACT['VALIDATE'],
                    ACT['SEND_CHAT'],
                    ACT['GUILD']['DONATE'],
                    ACT['REQUEST']['GUILD_NAMES'],
                    ACT['REQUEST']['CHAR'],
                    ACT['POST']['SEND'])):
                self.log.warning(''.join([
                    "Aktionsbefehl wird ignoriert, weil noch auf eine ",
                    "Serverantwort gewartet wird: ",
                    str(action)
                ]))
                return

        elif self.fight_lock:
            self.log.warning(''.join([
                "Aktionsbefehl wird ignoriert, weil ein wichtiges ",
                "Ereignis stattfindet:",
                str(action)
            ]))
            return

        data_str = str(action).zfill(3) + ';'.join(params)
        self.last_act = action

        fail_try = 1

        if self.session_id == "":
            self.session_id = "00000000000000000000000000000000"

            self.log.debug("SID: " + str(self.session_id))
            self.log.debug("Action: " + str(action))
            self.log.debug("Action+Daten: " + str(data_str))

        # TODO: This "if" switches base URL
        # self.param_poll_tunnel_url / param_php_tunnel_url
        if ((action == ACT['GET_CHAT_HISTORY'])
                and (self.param_poll_tunnel_url != "")):
            # TODO: move payload creation to method
            # self.param_poll_tunnel_url
            req_string = self.session_id + data_str
            random_string = '%2'
            rnd_string = str(round(random.random() * 0x77359400))
            rnd_string += str(int(time.time() * 1000))

            payload = {
                'req': req_string,
                'random': random_string,
                'rnd': rnd_string
            }

            self.poll_lock = True
        else:
            # self.param_php_tunnel_url
            req_string = self.session_id + data_str
            random_string = '%2'
            rnd_string = str(round(random.random() * 0x77359400))
            rnd_string += str(int(time.time() * 1000))

            payload = {
                'req': req_string,
                'random': random_string,
                'rnd': rnd_string
            }

            if action != ACT['GET_CHAT_HISTORY']:
                self.send_lock = True

        if self.mp_api_user_id != "notset":
            payload['mp_api_user_id'] = self.mp_api_user_id

        if self.mp_api_user_token != "notset":
            payload['mp_api_user_token'] = self.mp_api_user_token

        while fail_try < self.param_fail_tries:
            resp = requests.get(self.baseuri, params=payload)
            self.log.debug(resp.url)

            # TODO : test success of request here !!
            success = True

            if success:
                if ((action == ACT['GET_CHAT_HISTORY'])
                        and (self.param_poll_tunnel_url != "")):
                    self.poll_lock = False
                else:
                    self.send_lock = False

                data = resp.text()

                self.log.debug(str("Antwort auf %s: %s" % (action, data)))

                if data == "":
                    self.log.error(
                        "Fehler: Keine (leere) Antwort vom Tunnelskript.")
                    success = False
                else:
                    return data

            if not success:
                if fail_try < self.param_fail_tries:
                    self.log.warning(''.join([
                        "PHP-Request fehlgeschlagen (Versuch",
                        str(fail_try), "/",
                        str(self.param_fail_tries) + ").",
                        "Erneutes Senden..."
                    ]))
                    self.log.info("Erneut gesendet.")
                else:
                    self.log.warning(''.join([
                        "PHP Tunneling fehlgeschlagen. ",
                        "Versuche, neu zu verbinden."
                    ]))
                    self.session_id = ""
                    if ((action == ACT['GET_CHAT_HISTORY'])
                            and (self.param_poll_tunnel_url != "")):
                        self.poll_lock = False
                    else:
                        self.send_lock = False

                    raise RequestFailedException()
                fail_try += 1

    def load_configuration_file(self):
        '''
            configuration loader
        '''

        response = requests.get('http://' + self.server + '/client_cfg.php')

        # error handling

        return response.text
