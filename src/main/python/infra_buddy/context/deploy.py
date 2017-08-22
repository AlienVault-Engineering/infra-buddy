

class Deploy(object):
    def __init__(self,stack_name, template):
        # type: (str, Template) -> None
        super(Deploy, self).__init__()
        self.stack_name = stack_name
        self.config_directory = template.get_config_dir()
        self.parameter_file = template.get_parameter_file_path()
        self.template_file = template.get_template_file_path()
