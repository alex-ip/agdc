#!/usr/bin/env python

#===============================================================================
# Copyright (c)  2014 Geoscience Australia
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither Geoscience Australia nor the names of its contributors may be
#       used to endorse or promote products derived from this software
#       without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#===============================================================================

"""
    test_tile_record.py - tests for the TileRecord class
"""
# pylint: disable=too-many-public-methods
import re
import random
import os
import numpy as np
from eotools.execute import execute
import logging
import sys
import unittest
from agdc import dbutil
#import landsat_bandstack
from agdc.abstract_ingester import AbstractIngester
from agdc.abstract_ingester import IngesterDataCube
from landsat_dataset import LandsatDataset
from test_landsat_tiler import TestLandsatTiler
import ingest_test_data as TestIngest
from test_tile_contents import TestTileContents

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

#
# Constants
#

class TestArgs(object):
    """The sole instance of this class stores the config_path and debug
    arguments for passing to the datacube constructor."""
    pass

class TestIngester(AbstractIngester):
    """An ingester class from which to get a datacube object"""
    def __init__(self, datacube):
        AbstractIngester.__init__(self, datacube)
    def find_datasets(self, source_dir):
        pass
    def open_dataset(self, dataset_path):
        pass

class TestTileRecord(unittest.TestCase):
    """Unit tests for the TileRecord class"""
    # pylint: disable=too-many-instance-attributes
    ############################### User area #################################
    MODULE = 'tile_record'
    SUITE = 'TileRecord3'
    # Set to true if we want to populate expected directory with results,
    # without doing comparision. Set to False if we want to put (often
    # a subset of) results in output directory and compare against the
    # previously populated expected directory.
    POPULATE_EXPECTED = True
    ############################################

    INPUT_DIR = dbutil.input_directory(MODULE, SUITE)
    OUTPUT_DIR = dbutil.output_directory(MODULE, SUITE)
    EXPECTED_DIR = dbutil.expected_directory(MODULE, SUITE)

    if POPULATE_EXPECTED:
        destination_dir = 'expected'
    else:
        destination_dir = 'output'
    TEMP_DIR = dbutil.temp_directory(MODULE, SUITE, destination_dir)
    TILE_ROOT_DIR = dbutil.tile_root_directory(MODULE, SUITE, destination_dir)

    def setUp(self):
        #
        # Parse out the name of the test case and use it to name a logfile
        #
        match = re.search(r'\.([^\.]+)$', self.id())
        if match:
            name = match.group(1)
        else:
            name = 'TestIngester'
        logfile_name = "%s.log" % name
        self.logfile_path = os.path.join(self.OUTPUT_DIR, logfile_name)
        self.expected_path = os.path.join(self.EXPECTED_DIR, logfile_name)
        if self.POPULATE_EXPECTED:
            self.logfile_path = os.path.join(self.EXPECTED_DIR, logfile_name)
        #
        # Set up a handler to log to the logfile, and attach it to the
        # root logger.
        #
        #logging.basicConfig()
        self.handler = logging.FileHandler(self.logfile_path, mode='w')
        self.handler.setLevel(logging.INFO)
        self.handler.setFormatter(logging.Formatter('%(message)s'))
        LOGGER.addHandler(self.handler)

        # Add a streamhandler to write output to console
        
        self.stream_handler = logging.StreamHandler(stream=sys.stdout)
        self.stream_handler.setLevel(logging.INFO)
        self.stream_handler.setFormatter(logging.Formatter('%(message)s'))
        LOGGER.addHandler(self.stream_handler)

        # Create an empty database
        self.test_conn = None
        self.test_dbname = dbutil.random_name("test_tile_record")
        LOGGER.info('Creating %s', self.test_dbname)
        dbutil.TESTSERVER.create(self.test_dbname,
                                     self.INPUT_DIR, "hypercube_empty.sql")

        # Set the datacube configuration file to point to the empty database
        configuration_dict = {'dbname': self.test_dbname,
                              'temp_dir': self.TEMP_DIR,
                              'tile_root': self.TILE_ROOT_DIR}
        config_file_path = dbutil.update_config_file2(configuration_dict,
                                                     self.INPUT_DIR,
                                                     self.OUTPUT_DIR,
                                                     "test_datacube.conf")

        # Set an instance of the datacube and pass it to an ingester instance
        test_args = TestArgs()
        test_args.config_file = config_file_path
        test_args.debug = False
        test_datacube = IngesterDataCube(test_args)
        self.ingester = TestIngester(datacube=test_datacube)
        self.collection = self.ingester.collection
        

    def tearDown(self):
        #
        # Flush the handler and remove it from the root logger.
        #
        self.handler.flush()
        self.stream_handler.flush()
        if self.test_dbname:
            if self.POPULATE_EXPECTED:
                dbutil.TESTSERVER.save(self.test_dbname, self.EXPECTED_DIR,
                            'hypercube_tile_record.sql')
            else:
                #TODO: make dbase comaprision
                kkk=-1
            LOGGER.info('About to drop %s', self.test_dbname)
            dbutil.TESTSERVER.drop(self.test_dbname)
        LOGGER.removeHandler(self.handler)
        LOGGER.removeHandler(self.stream_handler)

    def xxxtest_insert_tile_record(self):
        """Test the Landsat tiling process method by comparing output to a
        file on disk."""
        # pylint: disable=too-many-locals
        # Test a single dataset for tile_record creation
        processing_level = 'PQA'
        dataset_path = TestIngest.DATASETS_TO_INGEST[processing_level][0]
        LOGGER.info('Testing Dataset %s', dataset_path)
        dset = LandsatDataset(dataset_path)
        # Create a DatasetRecord instance so that we can access its
        # list_tile_types() method. In doing this we need to create a
        # collection object and entries on the acquisition and dataset
        # tables of the database.
        self.collection.begin_transaction()
        acquisition = \
            self.collection.create_acquisition_record(dset)
        dset_record = acquisition.create_dataset_record(dset)

        # Get tile types
        dummy_tile_type_list = dset_record.list_tile_types()
        # Assume dataset has tile_type = 1 only:
        tile_type_id = 1
        dataset_bands_dict = dset_record.get_tile_bands(tile_type_id)
        ls_bandstack = dset.stack_bands(dataset_bands_dict)
        temp_dir = os.path.join(self.ingester.datacube.tile_root,
                                'ingest_temp')
        # Form scene vrt
        ls_bandstack.buildvrt(self.collection.get_temp_tile_directory())
        # Reproject scene data onto selected tile coverage
        tile_footprint_list = dset_record.get_coverage(tile_type_id)
        LOGGER.info('coverage=%s', str(tile_footprint_list))
        for tile_footprint in tile_footprint_list:
            tile_contents = \
                self.collection.create_tile_contents(tile_type_id,
                                                     tile_footprint,
                                                     ls_bandstack)
            LOGGER.info('reprojecting for %s tile %s',
                        processing_level, str(tile_footprint))
            #Need to call reproject to set tile_contents.tile_extents
            tile_contents.reproject()
            if tile_contents.has_data():
                dummy_tile_record = \
                    dset_record.create_tile_record(tile_contents)
        self.collection.commit_transaction()
        #TODO compare database with expected
        
    def test_aaa(self):
        pass

    def test_bbb(self):
        pass

    def test_make_mosaics(self):
        """Make mosaic tiles from two adjoining scenes."""
        # pylint: disable=too-many-locals
        dataset_list = \
            [TestIngest.DATASETS_TO_INGEST[level][i] for i in range(6)
             for level in ['PQA', 'NBAR', 'ORTHO']]
        dataset_list.extend(TestIngest.MOSAIC_SOURCE_NBAR)
        dataset_list.extend(TestIngest.MOSAIC_SOURCE_PQA)
        dataset_list.extend(TestIngest.MOSAIC_SOURCE_ORTHO)
        random.shuffle(dataset_list)
        LOGGER.info("Ingesting following datasets:")
        for dset in dataset_list:
            LOGGER.info('%d) %s', dataset_list.index(dset), dset)
        for dataset_path in dataset_list:
            LOGGER.info('Ingesting Dataset %d:\n%s',
                        dataset_list.index(dataset_path), dataset_path)
            dset = LandsatDataset(dataset_path)
            self.collection.begin_transaction()
            acquisition = \
                self.collection.create_acquisition_record(dset)
            dset_record = acquisition.create_dataset_record(dset)
            # Get tile types
            dummy_tile_type_list = dset_record.list_tile_types()
            # Assume dataset has tile_type = 1 only:
            tile_type_id = 1
            dataset_bands_dict = dset_record.get_tile_bands(tile_type_id)
            ls_bandstack = dset.stack_bands(dataset_bands_dict)
            temp_dir = os.path.join(self.ingester.datacube.tile_root,
                                    'ingest_temp')
            # Form scene vrt
            ls_bandstack.buildvrt(temp_dir)
            # Reproject scene data onto selected tile coverage
            tile_footprint_list = dset_record.get_coverage(tile_type_id)
            LOGGER.info('coverage=%s', str(tile_footprint_list))
            for tile_ftprint in tile_footprint_list:
                #Only do that footprint for which we have benchmark mosaics
                if tile_ftprint not in [(141, -38)]:
                    continue
                tile_contents = \
                    self.collection.create_tile_contents(tile_type_id,
                                                         tile_ftprint,
                                                         ls_bandstack)
                LOGGER.info('Calling reproject for %s tile %s...',
                            dset_record.mdd['processing_level'], tile_ftprint)
                tile_contents.reproject()
                LOGGER.info('...finished')
                if tile_contents.has_data():
                    LOGGER.info('tile %s has data',
                                tile_contents.temp_tile_output_path)
                    tile_record = dset_record.create_tile_record(tile_contents)
                    mosaic_required = tile_record.make_mosaics()
                    if not mosaic_required:
                        continue

                    # Test mosaic tiles against benchmark
                    # At this stage, transaction for this dataset not yet
                    # commited and so the tiles from this dataset, including
                    # any mosaics are still in the temporary location.
                    if self.POPULATE_EXPECTED:
                        continue

                    mosaic_benchmark = \
                        TestTileContents.swap_dir_in_path(tile_contents
                                              .mosaic_final_pathname,
                                              'output',
                                              'expected')
                    mosaic_new = tile_contents.mosaic_temp_pathname
                    LOGGER.info("Comparing test output with benchmark:\n"\
                                    "benchmark: %s\ntest output: %s",
                                mosaic_benchmark, mosaic_new)
                    if dset_record.mdd['processing_level'] == 'PQA':
                        LOGGER.info("For PQA mosaic, calling load_and_check...")
                        ([data1, data2], dummy_nlayers) = \
                            TestLandsatTiler.load_and_check(
                            mosaic_benchmark,
                            mosaic_new,
                            tile_contents.band_stack.band_dict,
                            tile_contents.band_stack.band_dict)
                        LOGGER.info('Checking arrays ...')
                        if ~(data1 == data2).all():
                            self.fail("Difference in PQA mosaic "
                                      "from expected result: %s and %s"
                                      %(mosaic_benchmark, mosaic_new))
                        # Check that differences are due to differing treatment
                        # of contiguity bit.
                    else:
                        diff_cmd = ["diff",
                                    "-I",
                                    "[Ff]ilename",
                                    "%s" %mosaic_benchmark,
                                    "%s" %mosaic_new
                                    ]
                        result = execute(diff_cmd, shell=False)
                        assert result['stdout'] == '', \
                            "Differences between vrt files"
                        assert result['stderr'] == '', \
                            "Error in system diff command"
                else:
                    LOGGER.info('... tile has no data')
                    tile_contents.remove()
            self.collection.commit_transaction()

def the_suite():
    "Runs the tests"""
    test_classes = [TestTileRecord]
    suite_list = map(unittest.defaultTestLoader.loadTestsFromTestCase,
                     test_classes)
    suite = unittest.TestSuite(suite_list)
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(the_suite())








