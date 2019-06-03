from traits.api import File, Bool, Undefined, String

from capsul.study_config.study_config import StudyConfigModule
from capsul.subprocess.fsl import check_fsl_configuration

class FSLConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(FSLConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path'))
        self.study_config.add_trait('fsl_prefix', String(Undefined,
            desc='Prefix to add to FSL commands'))
        self.study_config.add_trait('use_fsl', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure FSL'))

    def initialize_module(self):
        """ Set up FSL environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.fsl' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.fsl')
            self.study_config.engine.init_module('capsul.engine.module.fsl')
        self.sync_from_engine()

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, '[fsl_config, fsl_prefix, use_fsl]')
        self.study_config.engine.fsl.on_trait_change(
            self.sync_from_engine, '[config, prefix, use]')
        #if self.study_config.use_fsl is True:
            #check_fsl_configuration(self.study_config)

    def sync_to_engine(self):
        self.study_config.engine.fsl.config = self.study_config.fsl_config
        self.study_config.engine.fsl.prefix= self.study_config.fsl_prefix
        self.study_config.engine.fsl.use = self.study_config.use_fsl

    def sync_from_engine(self):
        self.study_config.fsl_config = self.study_config.engine.fsl.config
        self.study_config.fsl_prefix = self.study_config.engine.fsl.prefix
        self.study_config.use_fsl = self.study_config.engine.fsl.use

