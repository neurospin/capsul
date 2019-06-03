import os
from traits.api import File, Undefined, Bool
from capsul.study_config.study_config import StudyConfigModule


class MatlabConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(MatlabConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('matlab_exec', File(
            Undefined,
            output=False,
            desc='Matlab command path',
            exists=True))
        self.study_config.add_trait("use_matlab", Bool(
            Undefined,
            desc="If True, Matlab configuration is set up on startup"))

    def initialize_module(self):
        """ Set up Matlab environment according to current
        configuration.
        """
        if 'capsul.engine.module.matlab' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.matlab')
            self.study_config.engine.init_module('capsul.engine.module.matlab')
        self.sync_from_engine()

        #if self.study_config.use_matlab is False:
            ## Configuration is explicitely asking not to use SPM
            #return

        #if self.study_config.use_matlab is Undefined:
            ## If use_matlab is not defined, Matlab configuration will
            ## be done if possible but there will be no error if it cannot be
            ## done.
            #force_configuration = False
        #else:
            ## If use_matlab is True configuration must be valid otherwise
            ## an EnvironmentError is raised
            #force_configuration = True

        #if self.study_config.matlab_exec is Undefined:
            ## matlab_exec is not set, it will not be possible to activate
            ##Matlab
            #self.study_config.use_matlab = False
            #if force_configuration:
                #raise EnvironmentError('matlab_exec must be defined in order '
                                       #'to use Matlab')
            #return

        #if not os.path.exists(self.study_config.matlab_exec):
            #self.study_config.use_matlab = False
            #if force_configuration:
                #raise EnvironmentError('"%s" does not exists. Matlab '
                                       #'configuration is not valid.' % \
                                       #self.study_config.matlab_exec)
            #return

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.sync_to_engine, 'matlab_exec')
        self.study_config.engine.matlab.on_trait_change(
            self.sync_from_engine, 'executable')

        #self.study_config.on_trait_change(self.initialize_module, 'use_matlab')


    def sync_to_engine(self):
        self.study_config.engine.matlab.executable \
            = self.study_config.matlab_exec

    def sync_from_engine(self):
        self.study_config.matlab_exec \
            = self.study_config.engine.matlab.executable
