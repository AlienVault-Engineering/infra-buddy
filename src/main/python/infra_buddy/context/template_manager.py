from infra_buddy.context.deploy import Deploy


class TemplateManager(object):
    def __init__(self, deploy_ctx):
        # type: (DeployContext) -> None
        super(TemplateManager, self).__init__()
        self.deploy_ctx = deploy_ctx

    def get_known_service(self, service_type):
        # type: (str) -> Deploy
        template, params , config_dir = self.locate_service(service_type)
        return Deploy(stack_name=self.deploy_ctx.stack_name, template_file=template, parameter_file=params,
                      config_directory=config_dir)

    def get_known_service_modification(self, modification_name):
        template, params , config_dir = self.locate_service(modification_name,modification=True)
        return Deploy(stack_name=self.deploy_ctx.generate_modification_stack_name(modification_name),
                      template_file=template,
                      parameter_file=params,
                      config_directory=config_dir)

    def get_resource_service(self, template_file, parameter_file, config_directory):
        return Deploy(self.deploy_ctx.resource_stack_name,
                      template_file=template_file,
                      parameter_file=parameter_file,
                      config_directory=config_directory)

    def locate_service(self, service_type, modification=False):
        return "","",""
