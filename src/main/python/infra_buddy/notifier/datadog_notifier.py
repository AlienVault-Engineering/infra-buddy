import datadog as dd


class DataDogNotifier(object):
    def __init__(self, key, deploy_context):
        # type: (DeployContext) -> None
        super(DataDogNotifier, self).__init__()
        self.deploy_context = deploy_context
        dd.initialize(api_key=key)

    def notify_event(self, title, type, message):
        dd.api.Event.create(title=title,
                            text=message,
                            alert_type=type,
                            tags=self._get_tags())

    def _get_tags(self):
        return ['application:{app},role:{role},environment:{env}'.format(
            app=self.deploy_context.application,
            role=self.deploy_context.role,
            env=self.deploy_context.environment)]
