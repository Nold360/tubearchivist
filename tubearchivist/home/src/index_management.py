"""
Functionality:
- initial elastic search setup
- index configuration is represented in INDEX_CONFIG
- index mapping and settings validation
- backup and restore
"""

import json
import os

from datetime import datetime

import requests

from home.src.config import AppConfig


# expected mapping and settings
INDEX_CONFIG = [
    {
        'index_name': 'channel',
        'expected_map': {
            "channel_id": {
                "type": "keyword",
            },
            "channel_name": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                        "normalizer": "to_lower"
                    },
                    "search_as_you_type": {
                        "type": "search_as_you_type",
                        "doc_values": False,
                        "max_shingle_size": 3
                    }
                }
            },
            "channel_banner_url": {
                "type": "keyword",
                "index": False
            },
            "channel_thumb_url": {
                "type": "keyword",
                "index": False
            },
            "channel_description": {
                "type": "text"
            },
            "channel_last_refresh": {
                "type": "date",
                "format": "epoch_second"
            }
        },
        'expected_set': {
            "analysis": {
                "normalizer": {
                    "to_lower": {
                        "type": "custom",
                        "filter": ["lowercase"]
                    }
                }
            },
            "number_of_replicas": "0"
        }
    },
    {
        'index_name': 'video',
        'expected_map': {
            "vid_thumb_url": {
                "type": "text",
                "index": False
            },
            "date_downloaded": {
                "type": "date"
            },
            "channel": {
                "properties": {
                    "channel_id": {
                        "type": "keyword",
                    },
                    "channel_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                                "normalizer": "to_lower"
                            },
                            "search_as_you_type": {
                                "type": "search_as_you_type",
                                "doc_values": False,
                                "max_shingle_size": 3
                            }
                        }
                    },
                    "channel_banner_url": {
                        "type": "keyword",
                        "index": False
                    },
                    "channel_thumb_url": {
                        "type": "keyword",
                        "index": False
                    },
                    "channel_description": {
                        "type": "text"
                    },
                    "channel_last_refresh": {
                        "type": "date",
                        "format": "epoch_second"
                    }
                }
            },
            "description": {
                "type": "text"
            },
            "media_url": {
                "type": "keyword",
                "index": False
            },
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                        "normalizer": "to_lower"
                    },
                    "search_as_you_type": {
                        "type": "search_as_you_type",
                        "doc_values": False,
                        "max_shingle_size": 3
                    }
                }
            },
            "vid_last_refresh": {
                "type": "date"
            },
            "youtube_id": {
                "type": "keyword"
            },
            "published": {
                "type": "date"
            },
        },
        'expected_set': {
            "analysis": {
                "normalizer": {
                    "to_lower": {
                        "type": "custom",
                        "filter": ["lowercase"]
                    }
                }
            },
            "number_of_replicas": "0"
        }
    },
    {
        'index_name': 'download',
        'expected_map': {
            "timestamp": {
                "type": "date"
            },
            "channel_id": {
                "type": "keyword"
            },
            "channel_name": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                        "normalizer": "to_lower"
                    }
                }
            },
            "status": {
                "type": "keyword"
            },
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                        "normalizer": "to_lower"
                    }
                }
            },
            "vid_thumb_url": {
                "type": "keyword"
            },
            "youtube_id": {
                "type": "keyword"
            }
        },
        'expected_set': {
            "analysis": {
                "normalizer": {
                    "to_lower": {
                        "type": "custom",
                        "filter": ["lowercase"]
                    }
                }
            },
            "number_of_replicas": "0"
        }
    }
]


class ElasticIndex:
    """
    handle mapping and settings on elastic search for a given index
    """

    CONFIG = AppConfig().config
    ES_URL = CONFIG['application']['es_url']
    HEADERS = {'Content-type': 'application/json'}

    def __init__(self, index_name, expected_map, expected_set):
        self.index_name = index_name
        self.expected_map = expected_map
        self.expected_set = expected_set
        self.exists, self.details = self.index_exists()

    def index_exists(self):
        """ check if index already exists and return mapping if it does """
        index_name = self.index_name
        url = f'{self.ES_URL}/ta_{index_name}'
        response = requests.get(url)
        exists = response.ok

        if exists:
            details = response.json()[f'ta_{index_name}']
        else:
            details = False

        return exists, details

    def validate(self):
        """
        check if all expected mappings and settings match
        returns True when rebuild is needed
        """

        if self.expected_map:
            rebuild = self.validate_mappings()
            if rebuild:
                return rebuild

        if self.expected_set:
            rebuild = self.validate_settings()
            if rebuild:
                return rebuild

        return False

    def validate_mappings(self):
        """ check if all mappings are as expected """

        expected_map = self.expected_map
        now_map = self.details['mappings']['properties']

        for key, value in expected_map.items():
            # nested
            if list(value.keys()) == ['properties']:
                for key_n, value_n in value['properties'].items():
                    if key_n not in now_map[key]['properties'].keys():
                        print(key_n, value_n)
                        return True
                    if not value_n == now_map[key]['properties'][key_n]:
                        print(key_n, value_n)
                        return True

                continue

            # not nested
            if key not in now_map.keys():
                print(key, value)
                return True
            if not value == now_map[key]:
                print(key, value)
                return True

        return False

    def validate_settings(self):
        """ check if all settings are as expected """

        now_set = self.details['settings']['index']

        for key, value in self.expected_set.items():
            if key not in now_set.keys():
                print(key, value)
                return True

            if not value == now_set[key]:
                print(key, value)
                return True

        return False

    def rebuild_index(self):
        """ rebuild with new mapping """
        # backup
        self.reindex('backup')
        # delete original
        self.delete_index(backup=False)
        # create new
        self.create_blank()
        self.reindex('restore')
        # delete backup
        self.delete_index()

    def reindex(self, method):
        """ create on elastic search """
        index_name = self.index_name
        if method == 'backup':
            source = f'ta_{index_name}'
            destination = f'ta_{index_name}_backup'
        elif method == 'restore':
            source = f'ta_{index_name}_backup'
            destination = f'ta_{index_name}'

        query = {
            "source": {
                "index": source
            },
            "dest": {
                "index": destination
            }
        }
        data = json.dumps(query)
        url = self.ES_URL + '/_reindex?refresh=true'
        response = requests.post(url=url, data=data, headers=self.HEADERS)
        if not response.ok:
            print(response.text)

    def delete_index(self, backup=True):
        """ delete index passed as argument """
        if backup:
            url = f'{self.ES_URL}/ta_{self.index_name}_backup'
        else:
            url = f'{self.ES_URL}/ta_{self.index_name}'
        response = requests.delete(url)
        if not response.ok:
            print(response.text)

    def create_blank(self):
        """ apply new mapping and settings for blank new index """
        expected_map = self.expected_map
        expected_set = self.expected_set
        # stich payload
        payload = {}
        if expected_set:
            payload.update({"settings": expected_set})
        if expected_map:
            payload.update({"mappings": {"properties": expected_map}})
        # create
        url = f'{self.ES_URL}/ta_{self.index_name}'
        data = json.dumps(payload)
        response = requests.put(url=url, data=data, headers=self.HEADERS)
        if not response.ok:
            print(response.text)


class ElasticBackup:
    """ dump index to nd-json files for later bulk import """

    def __init__(self, index_config):
        self.config = AppConfig().config
        self.index_config = index_config
        self.timestamp = datetime.now().strftime('%Y%m%d')

    def get_all_documents(self, index_name):
        """ export all documents of a single index """
        headers = {'Content-type': 'application/json'}
        es_url = self.config['application']['es_url']
        # get PIT ID
        url = f'{es_url}/ta_{index_name}/_pit?keep_alive=1m'
        response = requests.post(url)
        json_data = json.loads(response.text)
        pit_id = json_data['id']
        # build query
        data = {
            "query": {"match_all": {}},
            "size": 100, "pit": {"id": pit_id, "keep_alive": "1m"},
            "sort": [ {"_id": {"order": "asc"}} ]
        }
        query_str = json.dumps(data)
        url = es_url + '/_search'
        # loop until nothing left
        all_results = []
        while True:
            response = requests.get(url, data=query_str, headers=headers)
            json_data = json.loads(response.text)
            all_hits = json_data['hits']['hits']
            if all_hits:
                for hit in all_hits:
                    search_after = hit['sort']
                    all_results.append(hit)
                # update search_after with last hit data
                data['search_after'] = search_after
                query_str = json.dumps(data)
            else:
                break
        # clean up PIT
        query_str = json.dumps({"id": pit_id})
        requests.delete(es_url + '/_pit', data=query_str, headers=headers)

        return all_results

    @staticmethod
    def build_bulk(all_results):
        """ build bulk query data from all_results """
        bulk_list = []

        for document in all_results:
            document_id = document['_id']
            es_index = document['_index']
            action = { "index" : { "_index": es_index, "_id": document_id } }
            source = document['_source']
            bulk_list.append(json.dumps(action))
            bulk_list.append(json.dumps(source))

        # add last newline
        bulk_list.append('\n')
        file_content = '\n'.join(bulk_list)

        return file_content

    def write_json_file(self, file_content, index_name):
        """ write json file to disk """
        cache_dir = self.config['application']['cache_dir']
        file_name = f'ta_{index_name}-{self.timestamp}.json'
        file_path = os.path.join(cache_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

    def post_bulk_restore(self, file_name):
        """ send bulk to es """
        cache_dir = self.config['application']['cache_dir']
        es_url = self.config['application']['es_url']
        headers = {'Content-type': 'application/x-ndjson'}
        file_path = os.path.join(cache_dir, file_name)

        with open(file_path, 'r', encoding='utf-8') as f:
            query_str = f.read()

        url = es_url + '/_bulk'
        request = requests.post(url, data=query_str, headers=headers)
        if not request.ok:
            print(request.text)

    def restore_from_file(self):
        """ restore all available backup files """
        cache_dir = self.config['application']['cache_dir']
        all_available_backups = [
            i for i in os.listdir(cache_dir) if
            i.startswith('ta_') and i.endswith('.json')
        ]
        for file_name in all_available_backups:
            self.post_bulk_restore(file_name)


def backup_all_indexes():
    """ backup all es indexes to disk """
    backup_handler = ElasticBackup(INDEX_CONFIG)

    for index in backup_handler.index_config:
        index_name = index['index_name']
        all_results = backup_handler.get_all_documents(index_name)
        file_content = backup_handler.build_bulk(all_results)
        backup_handler.write_json_file(file_content, index_name)


def restore_from_backup():
    """ restore indexes from backup file """
    # delete
    index_check(force_restore=True)
    # recreate
    backup_handler = ElasticBackup(INDEX_CONFIG)
    backup_handler.restore_from_file()


def index_check(force_restore=False):
    """ check if all indexes are created and have correct mapping """

    backed_up = False

    for index in INDEX_CONFIG:
        index_name = index['index_name']
        expected_map = index['expected_map']
        expected_set = index['expected_set']
        handler = ElasticIndex(index_name, expected_map, expected_set)
        # force restore
        if force_restore:
            handler.delete_index(backup=False)
            handler.create_blank()
            continue

        # create new
        if not handler.exists:
            print(f'create new blank index with name ta_{index_name}...')
            handler.create_blank()
            continue

        # validate index
        rebuild = handler.validate()
        if rebuild:
            # make backup before rebuild
            if not backed_up:
                print('running backup first')
                backup_all_indexes()
                backed_up = True

            print(f'applying new mappings to index ta_{index_name}...')
            handler.rebuild_index()
            continue

        # else all good
        print(f'ta_{index_name} index is created and up to date...')
