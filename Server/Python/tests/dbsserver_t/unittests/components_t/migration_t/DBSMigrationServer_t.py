#!/usr/bin/env python
"""
DBS 3 Migration Service unittests
"""
from dbsserver_t.utils.DBSRestApi import DBSRestApi
from dbsserver_t.utils.DBSDataProvider import DBSBlockDataProvider, create_child_data_provider
from dbsserver_t.utils.TestTools import expectedFailure

from itertools import chain

import os
import socket
import unittest

try:
    #This does not work on a dev-vm since dbsmigration as well as dbs contains the same package dbs, first package
    #in sys.path is taken, which does not contain all modules. For dev-vm we import directly using the full path
    from dbs.components.migration.DBSMigrationServer import MigrationTask
except ImportError:
    import imp
    ###check if patches are available
    input_source = \
        '/data/current/apps/dbsmigration/xlib/python2.6/site-packages/dbs/components/migration/DBSMigrationServer.py'

    if not os.path.exists(input_source):
        input_source = \
            '/data/current/apps/dbsmigration/lib/python2.6/site-packages/dbs/components/migration/DBSMigrationServer.py'

    MigrationServer = imp.load_source('DBSMigrationServer', input_source)
    MigrationTask = MigrationServer.MigrationTask

from DBSSecrets import dbs3_dp2_i2


class DBSMigrationServer_t(unittest.TestCase):
    _data_provider = None

    def __init__(self, methodName='runTest'):
        super(DBSMigrationServer_t, self).__init__(methodName)
        if not self._data_provider:
            self.setUpClass()

    @classmethod
    def setUpClass(cls):
        cls._data_provider = DBSBlockDataProvider(num_of_blocks=1, num_of_files=10, num_of_runs=10, num_of_lumis=10)
        cls._parent_data_provider = DBSBlockDataProvider(num_of_blocks=1, num_of_files=10,
                                                         num_of_runs=10, num_of_lumis=10)
        cls._child_data_provider = create_child_data_provider(cls._parent_data_provider)
        ###try to reload already inserted data
        try:
            cls._data_provider.load('migration_unittest_data.pkl')
            cls._parent_data_provider.load('migration_unittest_parent_data.pkl')
            cls._child_data_provider.load('migration_unittest_child_data.pkl')
        except IOError:
            pass
        config = os.environ['DBS_TEST_CONFIG']
        service = os.environ.get("DBS_TEST_SERVICE","DBSMigrate")
        #migration_test=True for forcing to use dbs3_dp2_i2 as destination DB.
        # Allways use the writer account of dbs3_dp2_i2. No matter it is a DBSMigrate, DBSWriter or DBSReader.
        cls._migrate_api = DBSRestApi(config, service, migration_test=True)
        cls._migration_url = 'https://%s/dbs/dev/global/DBSWriter' % (socket.getfqdn())
        #Please don't remove below commented line, until I have a better way to run the test on the development setting.
        #cls._migration_url = 'http://%s:8787/dbs/dev/global/DBSWriter' % (socket.getfqdn())
        cls._migration_reader_api = DBSRestApi(config, 'DBSReader', migration_test=True)
        #using DBSWriter instead of DBSReader to avoid db mismatching in DBSConfig.
        cls._reader_api = DBSRestApi(config, 'DBSWriter')
        cls._writer_api = DBSRestApi(config, 'DBSWriter')
        dbconfig = {'dbowner' : dbs3_dp2_i2['databaseOwner'],
                    'connectUrl' : dbs3_dp2_i2['connectUrl']['writer']}
        cls._migration_task = MigrationTask(dbconfig)

    def setUp(self):
        pass

    def test_00_insert_data_to_migrate(self):
        """test00: Insert data to migrate into source DBS instance"""
        for block in chain(self._data_provider.block_dump(),
                           self._parent_data_provider.block_dump(),
                           self._child_data_provider.block_dump()):
            try:
                self._writer_api.insert('bulkblocks', block)
            except Exception as ex:
                ###data already in DBS3 continue
                if str(ex).find('already exists')!=-1:
                    pass
                else:
                    raise ex

    @expectedFailure
    def test_01_migration_removal(self):
        """test01: Clean-up old migration requests. Test to remove migration requests between different DBS instances"""
        for status in sorted(self._migrate_api.list('status'), key=lambda status: status['migration_request_id']):
            data = {'migration_rqst_id': status['migration_request_id']}
            if status['migration_status'] in (0, 3):
                self._migrate_api.insert('remove', data)
            else:
                self.assertRaises(Exception, self._migrate_api.insert, 'remove', data)

    def test_02_insert_migration_requests(self):
        """test02: Test to request a migration between different DBS instances by block"""
        for block_data_provider in (self._data_provider, self._child_data_provider):
            block_data = block_data_provider.block_dump()[0]['block']['block_name']
            toMigrate = {'migration_url' : self._migration_url,
                         'migration_input' : block_data}
            ###schedule only the first block for migration
            self._migrate_api.insert('submit', toMigrate)

    def test_03_handle_migration_requests(self):
        """test03: Test to handle migration requests between different DBS instances by block"""
        for status in sorted(self._migrate_api.list('status'), key=lambda status: status['migration_request_id']):
            if status['migration_status']==0:
                self._migration_task.getResource()
                new_status = self._migrate_api.list('status', status['migration_request_id'])[0]
                self.assertEqual(new_status['migration_status'], 1)#1 means requests is processed
                self._migration_task.insertBlock()
                new_status = self._migrate_api.list('status', status['migration_request_id'])[0]
                self.assertEqual(new_status['migration_status'], 2)#2 means requests is successfully done
                self._migration_task.cleanup()

    def test_04_insert_migration_requests(self):
        """negative test04: Test to request a migration between different DBS instances by dataset"""
        datasets = set((block['dataset']['dataset'] for block in chain(self._data_provider.block_dump(),
                                                                       self._child_data_provider.block_dump())))
        for dataset in datasets:
            toMigrate = {'migration_url' : self._migration_url,
                         'migration_input' : dataset}
            try:
                self._migrate_api.insert('submit', toMigrate)
            except Exception, de:
                if "already in destination" in de.message:
                    pass


    def test_05_handle_migration_requests(self):
        """test05: Test to handle migration requests between different DBS instances by dataset"""
        for status in sorted(self._migrate_api.list('status'), key=lambda status: status['migration_request_id']):
            if status['migration_status']==0:
                self._migration_task.getResource()
                new_status = self._migrate_api.list('status', status['migration_request_id'])[0]
                self.assertEqual(new_status['migration_status'], 1)#1 means requests is processed
                self._migration_task.insertBlock()
                new_status = self._migrate_api.list('status', status['migration_request_id'])[0]
                self.assertEqual(new_status['migration_status'], 2)#2 means requests is successfully done
                self._migration_task.cleanup()

    def test_06_block_migration_validation(self):
        """test06: Try to validate the migrated data by comparing block dumps from source and destination DB"""
        for block_name in (block['block']['block_name'] for block in chain(self._data_provider.block_dump(),
                                                                           self._parent_data_provider.block_dump(),
                                                                           self._child_data_provider.block_dump())):
            block_dump_src = sorted(self._reader_api.list('blockdump', block_name=block_name))
            block_dump_dest = sorted(self._migration_reader_api.list('blockdump', block_name=block_name))
            self.assertEqual(block_dump_src, block_dump_dest)

if __name__ == "__main__":
    SUITE = unittest.TestLoader().loadTestsFromTestCase(DBSMigrationServer_t)
    unittest.TextTestRunner(verbosity=2).run(SUITE)