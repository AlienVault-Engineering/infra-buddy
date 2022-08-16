

class Deploy(object):


    
    def __init__(self,deploy_ctx):
        super(Deploy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.stack_name = None
        self.defaults = {}

    def do_deploy(self,dry_run=False):
        self.deploy_ctx.push_deploy_ctx(self)
        try:
            return self._internal_deploy(dry_run)
        finally:
            self.deploy_ctx.pop_deploy_ctx()

    def _internal_deploy(self,dry_run):
        pass

    def __str__(self):
        return "{} - {}".format(self.__class__.__name__,self.stack_name)

