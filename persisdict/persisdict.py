"""
   Author: Matthew Molyett
   Created: Fri Jan 19 09:55:49 EST 2018
"""
from __future__ import print_function
import argparse, sys, os, logging, datetime
import sqlite3, json

log = logging.getLogger('persisdict')
CUR_DIR = os.path.dirname(os.path.abspath(__file__))

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)

        return json.JSONEncoder.default(self, o)
        
class pdict(object):
    CacheName = "magic_json"
    CACHE_FILE = os.path.join(CUR_DIR, 'json_state.db')    

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        for key in self.cache_dict:
            self[key]
        self.cache_dict = {}
            
        if self.conn:
            if self.cursor:
                self.cursor.close()
            self.conn.close()
        
    def __init__(self, filepath=None, tablename=None):
        if filepath: self.CACHE_FILE=filepath
        if tablename: self.CacheName=tablename
        self.cache_dict = {}
        self.conn, self.cursor = None, None
        
        self.conn = sqlite3.connect(self.CACHE_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cursor = self.conn.cursor()
        
        # Create table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS {}
                     (json_blob text, key text PRIMARY KEY, created timestamp, modifed timestamp)'''.format(self.CacheName))
        # Save (commit) the changes
        self.conn.commit()
        self._keys = set()
        
    def __len__(self):
        return len(self.keys())
        
    def __del__(self):
        for key in self.cache_dict:
            self[key]
        
    def keys(self):
        if self._keys:
            return sorted(list(self._keys))
        self.cursor.execute("SELECT DISTINCT key from {}".format(self.CacheName), [])
        all_rows = self.cursor.fetchall()
        for row in all_rows:
            _key, = row
            # if not _key:
                # logging.error("Invalid key found! - {}".format(row))
                # continue
            self._keys.add(_key)
        return sorted(list(self._keys))
        
    def __contains__(self, key):
        if key is None:
            raise KeyError("None key used")
        return key in self.keys()
        
    def __iter__(self):
        for k in self.keys():
            yield k
            
    def _update_db(self, key, item, update_time):
        if key is None:
            raise KeyError("None key used")
        self.cache_dict[key]['value'] = item
        self.cache_dict[key]['modifed'] = update_time
        self.cursor.execute("UPDATE {} SET json_blob=?,modifed=? WHERE key = ?".format(self.CacheName),
                [json.dumps(self.cache_dict[key],cls=DateTimeEncoder), update_time, key])
        self.conn.commit()
    
    def _update_from_db(self, key):
        if key is None:
            raise KeyError("None key used")
        self.cursor.execute("SELECT json_blob from {} WHERE key=?".format(self.CacheName), [key])
        all_rows = self.cursor.fetchall()
        if not all_rows:
            raise KeyError(key)
        if not len(all_rows) == 1:
            raise KeyError("{} entries for key {}".format(len(all_rows), key))
        func_return = {'cached':False, 'result':None}
        json_blob, = all_rows[0]
        
        try:
            _ = json.loads(json_blob)
            _['modifed'] = datetime.datetime.strptime(_['modifed'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError as ve:
            try: 
                _['modifed'] = datetime.datetime.strptime(_['modifed'], "%Y-%m-%dT%H:%M:%S")
            except ValueError as ve:
                raise KeyError("Data corruption in entry for key {} {}".format(key, ve))
        except KeyError as ke:
            raise KeyError("Value corruption in entry for key {}".format(key))
        return _
            
    def __setitem__(self, key, item):
        if key is None:
            raise KeyError("None key used")
        update_time = datetime.datetime.utcnow()
        if not None == self.get(key, None):
            self._update_db(key, item, update_time)
        else:
            self.cache_dict[key] = {
                            'value':item,
                            'modifed':update_time
                            }
            self.cursor.execute("INSERT INTO {} VALUES (?,?,?,?)".format(self.CacheName),
                    [json.dumps(self.cache_dict[key],cls=DateTimeEncoder), key, update_time, update_time])
            self.conn.commit()
        if self._keys:
            self._keys.add(key)
        
    def __getitem__(self, key):
        if key is None:
            raise KeyError("None key used")
        if key in self.cache_dict:
            # flush cache to backing if it is mutable
            try:
                set([self.cache_dict[key]['value']])
            except TypeError:
                #check and see if database has already been updated
                db_state = self._update_from_db(key)
                if self.cache_dict[key]['modifed'] < db_state['modifed']:
                    self.cache_dict[key] = db_state
                else:
                    self._update_db(key, self.cache_dict[key]['value'], datetime.datetime.utcnow())
            
            return self.cache_dict[key]['value']
        
        db_state = self._update_from_db(key)
        
        try:
            self.cache_dict[key] = db_state
            return self.cache_dict[key]['value']
        except ValueError as ve:
            raise KeyError("Data corruption in entry for key {}".format(key))
        except KeyError as ke:
            raise KeyError("Value corruption in entry for key {}".format(key))
            
    def pop(self, key, default=None):
        if key is None:
            raise KeyError("None key used")
        if not key in self.cache_dict:
            if default: return default
            raise KeyError(key)
        
        _value_dict = self.cache_dict.pop(key)
        self.cursor.execute("DELETE FROM {} WHERE key=?".format(self.CacheName),
                [key,])
        self.conn.commit()
        if self._keys:
            self._keys.remove(key)
        return _value_dict['value']
               
    def get(self, key, default=None):
        if key is None:
            raise KeyError("None key used")
        try:
            return self[key]
        except KeyError:
            return default