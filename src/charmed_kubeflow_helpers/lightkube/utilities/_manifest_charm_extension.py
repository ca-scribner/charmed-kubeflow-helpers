import logging
from pathlib import Path
from typing import Optional

from jinja2 import Template
from lightkube.core.exceptions import ApiError
from lightkube import codecs, Client
from ops.charm import CharmBase
from ops.model import ActiveStatus, BlockedStatus

from ._check_resources import check_resources, get_first_worst_error
from ...exceptions import LeadershipError
from ...lightkube.exceptions import ReconcileError
from ...status_handling import CharmStatusType
from ..types import LightkubeResourcesType
from ...utilities import is_leader


class KubernetesResourceHandler:
    """Defines an API for handling Kubernetes resources in charm code

    To use this extension, the passed charm needs:
    * TODO: Add to this list
    * self.template_files: an iterable of jinja templates describing the k8s manifests to render
    * self.context_for_render(): a function that returns a dict of key:value pairs to be used as
                                 context for rendering the templates
                                 TODO: note atm this is a property in the old code
    """

    def __init__(
        self,
        charm: CharmBase,  # alternatively, we could just pass the things we need from charm
    ):
        # self._validate_charm(charm)  # TODO
        self._charm = charm

        try:
            self.log = self._charm.log
        except AttributeError:
            # TODO: This should write logs under parent charm's name
            self.log = logging.getLogger(__name__)

        self._lightkube_client = None

    def on_install(self):
        # TODO
        raise NotImplementedError()

    def on_update_status(self):
        # TODO
        raise NotImplementedError()

    def resource_status(
        self, resources: Optional[LightkubeResourcesType] = None
    ) -> CharmStatusType:
        """Computes the status of the managed resources as defined by the manifest, logging errors

        TODO: This method will not notice that we have an extra resource (eg: if our
              render_manifests() previously output some Resource123, but now render_manifests()
              does not output that resource.
        """
        self.log.info("Computing status")

        try:
            is_leader(self._charm)
        except LeadershipError as e:
            return e.status

        if resources is None:
            resources = self.render_manifests()

        charm_ok, errors = check_resources(self.lightkube_client, resources)
        if charm_ok:
            self.log.info("Status: active")
            status = ActiveStatus()
        else:
            # Hit one or more errors with resources.  Return status for worst and log all
            self.log.info("Charm is not active due to one or more issues:")

            # Log all errors, ignoring None's
            errors = [error for error in errors if error is not None]
            for i, error in enumerate(errors):
                self.log.info(f"Issue {i+1}/{len(errors)}: {error.msg}")

            # Return status based on the worst thing we encountered
            status = get_first_worst_error(errors).status

        return status

    def render_manifests(self) -> LightkubeResourcesType:
        """Renders this charm's manifests, returning them as a list of Lightkube Resources

        If overriding this class, you should replace it with a method that will always generate
        a list of all resources that should currently exist in the cluster.
        """
        self.log.info("Rendering manifests")
        context = self._charm.context_for_render
        self.log.debug(f"Rendering with context: {context}")
        manifest_parts = []
        for template_file in self.template_files:
            self.log.debug(f"Rendering manifest for {template_file}")
            template = Template(Path(template_file).read_text())
            rendered_template = template.render(**context)
            manifest_parts.append(rendered_template)
            self.log.debug(f"Rendered manifest:\n{manifest_parts[-1]}")
        return codecs.load_all_yaml("\n---\n".join(manifest_parts))

    def reconcile_resources(self, resources: Optional[LightkubeResourcesType] = None):
        """Reconcile our Kubernetes objects to achieve the desired state
        This can be invoked to both install or update objects in the cluster.  It uses an apply
        logic to update things only if necessary.  This method by default __does not__ remove
        objects that are no longer required - if handling that situation is required, it must be
        done separately.

        TODO: Handle deleted objects
        """
        self.log.info("Reconciling")
        if resources is None:
            resources = self.render_manifests()
        self.log.debug(f"Applying {len(resources)} resources")

        try:
            # TODO: This feature is not generally available in lightkube yet.  Should we make a
            #  helper here until it is?
            self.lightkube_client.apply_many(resources)
        except ApiError as e:
            # Handle forbidden error as this likely means we do not have --trust
            if e.status.code == 403:
                self.log.error(
                    "Received Forbidden (403) error from lightkube when creating resources.  "
                    "This may be due to the charm lacking permissions to create cluster-scoped "
                    "roles and resources.  Charm must be deployed with `--trust`"
                )
                self.log.error(f"Error received: {str(e)}")
                raise ReconcileError(
                    "Cannot create required resources.  Charm may be missing "
                    "`--trust`",
                    BlockedStatus,
                )
            else:
                raise e
        self.log.info("Reconcile completed successfully")

    @property
    def lightkube_client(self) -> Client:
        if self._lightkube_client is None:
            self._lightkube_client = Client(field_manager=self.app_name)
        return self._lightkube_client

    @lightkube_client.setter
    def lightkube_client(self, value: Client):
        if isinstance(value, Client):
            self._lightkube_client = value
        else:
            raise ValueError("lightkube_client must be a lightkube.Client")

    @property
    def template_files(self):
        return self._charm.template_files

    @staticmethod
    def _validate_charm(charm: CharmBase):
        """Validates the charm to ensure it has the required attributes"""
        raise NotImplementedError()
