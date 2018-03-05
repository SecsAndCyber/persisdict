from unittest import TestCase
from tempfile import NamedTemporaryFile

import persisdict

import os, shutil, glob

class TestPersisdictTestCase(TestCase):
    def test_seperate_backing_files(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA['state'] = "Created"
            with NamedTemporaryFile() as ntf_b:
                tableB = persisdict.pdict(filepath=ntf_b.name)
                try:
                    assert tableB['state'] == "Created"
                    raise ValueError("Expected KeyError")
                except KeyError:
                    pass
                    
    def test_same_backing_files(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA['state'] = "Created"
            
            tableB = persisdict.pdict(filepath=ntf.name)
            assert tableB['state'] == "Created"
            
            
                    
    def test_length(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA[1] = "Created"
            assert len(tableA) == 1
            tableA[2] = "Created"
            assert len(tableA) == 2
            tableA[3] = "Created"
            assert len(tableA) == 3
            tableA[4] = "Created"
            assert len(tableA) == 4
            tableA[5] = "Created"
            assert len(tableA) == 5
                    
    def test_mutable_changes(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA['state'] = ["Created"]
            l = tableA['state']
            l.append("Another")
            
            
            tableA = persisdict.pdict(filepath=ntf.name)
            assert tableA['state'] == ['Created', 'Another']
                    
    def test_mutable_multiaccess(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA['state'] = ["Created"]
            l = tableA['state']
            l.append("Another")
            
            # Since tableA['state'] has not been written to and tableA is not being cleaned up
            # the changes to mutable object l/tableA['state'] have not been flushed!
            tableB = persisdict.pdict(filepath=ntf.name)
            assert tableB['state'] == ['Created']
            
            # By changing tableA['state'] the database is change
            tableA['state'] = l
            assert tableA['state'] == ['Created', 'Another']
            
            # Since the database has changed tableB detects its cache is out of data and updates
            assert tableB['state'] == ['Created', 'Another']
            
            tableC = persisdict.pdict(filepath=ntf.name)
            # tableC requests from the database
            assert tableC['state'] == ['Created', 'Another']
            
    def test_mutable_multiaccess_del(self):
        with NamedTemporaryFile() as ntf:
            tableA = persisdict.pdict(filepath=ntf.name)
            tableA['state'] = ["Created"]
            l = tableA['state']
            l.append("Another")
            
            # Since tableA['state'] has not been written to and tableA is not being cleaned up
            # the changes to mutable object l/tableA['state'] have not been flushed!
            tableB = persisdict.pdict(filepath=ntf.name)
            assert tableB['state'] == ['Created']
            
            # By changing tableA['state'] the database is change
            tableA['state'] = l
            assert tableA['state'] == ['Created', 'Another']
            
            # Delete tableB without accessing it again to see if it flushes its stale cache
            del tableB
            
            tableC = persisdict.pdict(filepath=ntf.name)
            # tableC requests from the database, confirm the stale cache was not flushed
            assert tableC['state'] == ['Created', 'Another']