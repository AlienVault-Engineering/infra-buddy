

class Deploy(object):
    def __init__(self,stack_name, template_file, parameter_file, config_directory=None):
        # type: (str, str, str) -> None
        super(Deploy, self).__init__()
        self.stack_name = stack_name
        self.config_directory = config_directory
        self.parameter_file = parameter_file
        self.template_file = template_file
