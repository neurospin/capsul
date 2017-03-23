#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  This software and supporting documentation were developed by
#      CEA/DSV/SHFJ and IFR 49
#      4 place du General Leclerc
#      91401 Orsay cedex
#      France
#
# This software is governed by the CeCILL license version 2 under
# French law and abiding by the rules of distribution of free software.
# You can  use, modify and/or redistribute the software under the
# terms of the CeCILL license version 2 as circulated by CEA, CNRS
# and INRIA at the following URL "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license version 2 and that you accept its terms.

"""
capsul.process.runprocess is not a real python module, but rather an executable script with commandline arguments and options parsing. It is provided as a module just to be easily called via the python command in a portable way:
python -m capsul.process.runprocess <process name> <process arguments>
"""

from __future__ import print_function

from capsul.api import get_process_instance
from capsul.api import StudyConfig
from capsul.api import Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine

import sys, re, types
from optparse import OptionParser, OptionGroup
try:
    import yaml
except ImportError:
    yaml = None
    import json
import six


def get_process_with_params(process_name, study_config, iterated_params=[],
                            *args, **kwargs):
    ''' Instantiate a process, or an iteration over processes, and fill in its
    parameters.

    Parameters
    ----------
    process_name: string
        name (mosule and class) of the process to instantiate
    study_config: StudyConfig instance
    iterated_params: list (optional)
        parameters names which should be iterated on. If this list is not
        empty, an iteration process is built. All parameters values
        corresponding to the selected names should be lists with the same size.
    *args:
        sequential parameters for the process. In iteration, "normal"
        parameters are set with the same value for all iterations, and iterated
        parameters dispatch their values to each iteration.
    **kwargs:
        named parameters for the process. Same as above for iterations.

    Returns
    -------
    process: Process instance
    '''
    process = study_config.get_process_instance(process_name)
    signature = process.user_traits()
    params = list(signature.keys())

    # check for iterations
    if iterated_params:

        pipeline = study_config.get_process_instance(Pipeline)
        pipeline.add_iterative_process('iteration', process, iterated_params)
        process = pipeline

    else:
        # not iterated
        for i, arg in enumerate(args):
            setattr(process, params[i], arg)
        for k, arg in six.iteritems(kwargs):
            setattr(process, k, arg)

    completion_engine = ProcessCompletionEngine.get_completion_engine(process)
    completion_engine.complete_parameters()

    return process


def run_process_with_distribution(
        study_config, process, use_soma_workflow=False, resource_id=None,
        password=None, config=None, rsa_key_pass=None, queue=None,
        input_file_processing=None, output_file_processing=None,
        keep_workflow=False, keep_failed_workflow=False):
    ''' Run the given process, either sequentially or distributed through
    Soma-Workflow.

    Parameters
    ----------
    study_config: StudyConfig instance
    process: Process instance
        the process to execute (or pipeline, or iteration...)
    use_soma_workflow: bool or None (default=None)
        if False, run sequentially, otherwise use Soma-Workflow. Its
        configuration has to be setup and valid for non-local execution, and
        additional file transfer options may be used.
    resource_id: string (default=None)
        soma-workflow resource ID, defaults to localhost
    password: string
        password to access the remote computing resource. Do not specify it if
        using a ssh key.
    config: dict (optional)
        Soma-Workflow config: Not used for now...
    rsa_key_pass: string
        RSA key password, for ssh key access
    queue: string
        Queue to use on the computing resource. If not specified, use the
        default queue.
    input_file_processing: brainvisa.workflow.ProcessToSomaWorkflow processing code
        Input files processing: local_path (NO_FILE_PROCESSING),
        transfer (FILE_TRANSFER), translate (SHARED_RESOURCE_PATH),
        or translate_shared (BV_DB_SHARED_PATH).
    output_file_processing: same as for input_file_processing
        Output files processing: local_path (NO_FILE_PROCESSING),
        transfer (FILE_TRANSFER), or translate (SHARED_RESOURCE_PATH).
        The default is local_path.
    keep_workflow: bool
        keep the workflow in the computing resource database after execution.
        By default it is removed.
    keep_failed_workflow: bool
        keep the workflow in the computing resource database after execution,
        if it has failed. By default it is removed.
    '''
    if use_soma_workflow is not None:
        study_config.use_soma_workflow = use_soma_workflow
    if study_config.use_soma_workflow:
        swm = study_config.modules['SomaWorkflowConfig']
        resource_id = swm.get_resource_id(resource_id, set_it=True)
        if password is not None or rsa_key_pass is not None:
            swm.set_computing_resource_password(resource_id, password,
                                                rsa_key_pass)
        if queue is not None:
            if not hasattr(
                    study_config.somaworkflow_computing_resources_config,
                    resource_id):
                setattr(study_config.somaworkflow_computing_resources_config,
                        resource_id, {})
            getattr(study_config.somaworkflow_computing_resources_config,
                    resource_id).queue = queue

    res = study_config.run(process)
    return res


def convert_commandline_parameter(i):
    if len(i) > 0 and ( i[0] in '[({' or i in ( 'None', 'True', 'False' ) ):
        try:
            res=eval(i)
        except:
            res=i
    else:
        res = i
    return res


# main

usage = '''Usage: %prog [options] processname [arg1] [arg2] ... [argx=valuex] [argy=valuey] ...

Example:
%prog threshold ~/data/irm.ima /tmp/th.nii threshold1=80

Named arguments (in the shape argx=valuex) may address sub-processes of a pipeline, using the dot separator:

PrepareSubject.t1mri=/home/myself/mymri.nii

For a more precise description, please look at the web documentation:
http://brainvisa.info/capsul/user_doc/axon_manual2.html#brainvisa-commandline
'''

parser = OptionParser(description='Run a single CAPSUL process',
    usage=usage)
group1 = OptionGroup(parser, 'Config',
                     description='Processing configuration, database options')
group1.add_option('--studyconfig', dest='studyconfig',
    help='load StudyConfig configuration from the given file (JSON)')
#group1.add_option('--enablegui', dest='enablegui', action='store_true',
    #default=False,
    #help='enable graphical user interface for interactive processes')
parser.add_option_group(group1)

group2 = OptionGroup(parser, 'Processing',
                     description='Processing options, distributed execution')
group2.add_option('--swf', '--soma_workflow', dest='soma_workflow',
                  action='store_true', help='use soma_workflow. Soma-Workflow '
                  'configuration has to be setup and valid for non-local '
                  'execution, and additional login and file transfer options '
                  'may be used')
group2.add_option('-r', '--resource_id', dest='resource_id', default=None,
                  help='soma-workflow resource ID, defaults to localhost')
group2.add_option('-p', '--password', dest='password', default=None,
                  help='password to access the remote computing resource. '
                  'Do not specify it if using a ssh key')
group2.add_option('--rsa-pass', dest='rsa_key_pass', default=None,
                  help='RSA key password, for ssh key access')
group2.add_option('--queue', dest='queue', default=None,
                  help='Queue to use on the computing resource. If not '
                  'specified, use the default queue.')
group2.add_option('--input-processing', dest='input_file_processing',
                  default=None, help='Input files processing: local_path, '
                  'transfer, translate, or translate_shared. The default is '
                  'local_path if the computing resource is the localhost, or '
                  'translate_shared otherwise.')
group2.add_option('--output-processing', dest='output_file_processing',
                  default=None, help='Output files processing: local_path, '
                  'transfer, or translate. The default is local_path.')
group2.add_option('--keep-workflow', dest='keep_workflow', action='store_true',
                  help='keep the workflow in the computing resource database '
                  'after execution. By default it is removed.')
group2.add_option('--keep-failed-workflow', dest='keep_failed_workflow',
                  action='store_true',
                  help='keep the workflow in the computing resource database '
                  'after execution, if it has failed. By default it is '
                  'removed.')
parser.add_option_group(group2)

group3 = OptionGroup(parser, 'Iteration',
                     description='Iteration')
group3.add_option('-i', '--iterate', dest='iterate_on', action='append',
                  help='Iterate the given process, iterating over the given '
                  'parameter(s). Multiple parameters may be iterated joinly '
                  'using several -i options. In the process parameters, '
                  'values are replaced by lists, all iterated lists should '
                  'have the same size.\n'
                  'Ex:\n'
                  'axon-runprocess -i par_a -i par_c a_process par_a="[1, 2]" '
                  'par_b="something" par_c="[\\"one\\", \\"two\\"]"')
parser.add_option_group(group3)

#group4 = OptionGroup(parser, 'Help',
                     #description='Help and documentation options')
#group4.add_option('--list-processes', dest='list_processes',
    #action='store_true',
    #help='List processes and exit. sorting / filtering are controlled by the '
    #'following options.')
#group4.add_option('--sort-by', dest='sort_by',
    #help='List processed by: id, name, toolbox, or role')
#group4.add_option('--proc-filter', dest='proc_filter', action='append',
    #help='filter processes list. Several filters may be used to setup several '
    #'rules. Rules have the shape: attribute="filter_expr", filter_expr is a '
    #'regex.\n'
    #'Ex: id=".*[Ss]ulci.*"')
#group4.add_option('--hide-proc-attrib', dest='hide_proc_attrib',
    #action='append', default=[],
    #help='in processes list, hide selected attribute (several values allowed)')
#group4.add_option('--process-help', dest='process_help',
    #action='append',
    #help='display specified process help')
#parser.add_option_group(group4)

parser.disable_interspersed_args()
(options, args) = parser.parse_args()

#if options.enablegui:
    #neuroConfig.gui = True
    #from soma.qt_gui.qt_backend import QtGui
    #qapp = QtGui.QApplication([])

#if options.list_processes:
    #sort_by = options.sort_by
    #if not sort_by:
        #sort_by = 'id'
    #else: print('sort-by:', sort_by)
    #processinfo.process_list_help(sort_by, sys.stdout,
                                  #proc_filter=options.proc_filter,
                                  #hide=options.hide_proc_attrib)
    #sys.exit(0)

#if options.process_help:
    #for process in options.process_help:
        #processinfo.process_help(process)
    #sys.exit(0)


if options.studyconfig:
    study_config = StudyConfig()
    if yaml:
        scdict = yaml.load(open(options.studyconfig))
    else:
        scdict = json.load(open(options.studyconfig))
    study_config.set_study_configuration(scdict)
else:
    study_config = StudyConfig()
    study_config.read_configuration()

args = tuple((convert_commandline_parameter(i) for i in args))
kwre = re.compile('([a-zA-Z_](\.?[a-zA-Z0-9_])*)\s*=\s*(.*)$')
kwargs = {}
todel = []
for arg in args:
    if type(arg) in types.StringTypes:
        m = kwre.match(arg)
        if m is not None:
            kwargs[m.group(1)] = convert_commandline_parameter(m.group(3))
            todel.append(arg)
args = [arg for arg in args if arg not in todel]

# get the main process
process_name = args[0]
args = args[1:]

iterated = options.iterate_on
process = get_process_with_params(process_name, study_config, iterated, *args,
                                  **kwargs)

resource_id = options.resource_id
login = options.login
password = options.password
rsa_key_pass = options.rsa_key_pass
queue = options.queue
file_processing = []

if options.soma_workflow:

    study_config.use_soma_workflow = True

else:
    file_processing = [None, None]

run_process_with_distribution(
    study_config, process, options.soma_workflow, resource_id=resource_id,
    login=login, password=password, rsa_key_pass=rsa_key_pass,
    queue=queue, input_file_processing=file_processing[0],
    output_file_processing=file_processing[1],
    keep_workflow=options.keep_workflow,
    keep_failed_workflow=options.keep_failed_workflow)


sys.exit(neuroConfig.exitValue)

