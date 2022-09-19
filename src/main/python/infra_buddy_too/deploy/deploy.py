

class Deploy(object):


    
    def __init__(self,deploy_ctx):
        super(Deploy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.stack_name = None
        self.defaults = {}
        # Flag to indicate that we should not actually deploy (see deploy-environments['skip'])
        self.dry_run = False

    def do_deploy(self,dry_run=False):
        self.deploy_ctx.push_deploy_ctx(self)
        try:
            return self._internal_deploy(dry_run or self.dry_run)
        finally:
            self.deploy_ctx.pop_deploy_ctx()

    def _internal_deploy(self,dry_run):
        pass

    def __str__(self):
        if self.dry_run:
            return f"{self.__class__.__name__} - {self.stack_name } - Environment Skipped"
        return f"{self.__class__.__name__} - {self.stack_name }"

