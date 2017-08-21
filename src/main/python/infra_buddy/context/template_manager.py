from infra_buddy.context.deploy import Deploy


class TemplateManager(object):
    def __init__(self,deploy_ctx):
        # type: (DeployContext) -> None
        super(TemplateManager, self).__init__()
        self.deploy_ctx = deploy_ctx

    def get_known_service(self,service_type):
        # type: (str) -> Deploy
        template = ""
        params = ""
        config_dir = ""
        deploy = Deploy(template_file=template,parameter_file=params,config_directory=config_dir)
        return deploy


    def get_known_service_modification(self,modification_name):
        template = ""
        params = ""
        config_dir = ""
        deploy = Deploy(template_file=template,parameter_file=params,config_directory=config_dir)
        return deploy