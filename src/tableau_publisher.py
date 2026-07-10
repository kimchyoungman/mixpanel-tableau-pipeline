"""
Tableau Cloud Publisher module.
Handles authentication and publishing of Hyper files to Tableau Cloud.
"""
import logging
import os

import tableauserverclient as TSC

logger = logging.getLogger(__name__)


class TableauPublisher:
    """Publishes Hyper files to Tableau Cloud."""

    def __init__(
        self,
        server_url: str | None = None,
        site_id: str | None = None,
        token_name: str | None = None,
        token_value: str | None = None
    ):
        """
        Initialize the publisher.

        Args:
            server_url: Tableau Server URL (e.g. https://your-pod.online.tableau.com)
            site_id: Tableau Site ID (Content Url)
            token_name: PAT Name
            token_value: PAT Secret
        """
        # Load from env if not provided
        self.server_url = server_url or os.getenv("TABLEAU_SERVER_URL")
        self.site_id = site_id or os.getenv("TABLEAU_SITE_ID")
        self.token_name = token_name or os.getenv("TABLEAU_TOKEN_NAME")
        self.token_value = token_value or os.getenv("TABLEAU_TOKEN_VALUE")

        if not all([self.server_url, self.site_id, self.token_name, self.token_value]):
            raise ValueError(
                "Missing Tableau credentials. Please ensure TABLEAU_SERVER_URL, "
                "TABLEAU_SITE_ID, TABLEAU_TOKEN_NAME, and TABLEAU_TOKEN_VALUE are set."
            )

    def publish(
        self,
        file_path: str,
        project_name: str = "Default",
        datasource_name: str = "mixpanel_hyper",
        mode: str = "Append"
    ) -> str:
        """
        Publish a Hyper file to Tableau Cloud.

        Args:
            file_path: Path to the .hyper file
            project_name: Name of the Tableau project (folder) to publish to
            datasource_name: Name of the datasource on Tableau Server
            mode: 'Append' or 'Overwrite'

        Returns:
            ID of the published datasource.
        """
        # Setup authentication
        tableau_auth = TSC.PersonalAccessTokenAuth(
            token_name=self.token_name,
            personal_access_token=self.token_value,
            site_id=self.site_id
        )
        server = TSC.Server(self.server_url, use_server_version=True)

        # Map mode string to TSC constant
        publish_mode = TSC.Server.PublishMode.Append if mode == "Append" else TSC.Server.PublishMode.Overwrite

        logger.info(f"Connecting to Tableau Cloud ({self.server_url})...")

        with server.auth.sign_in(tableau_auth):
            # Find the project ID
            all_projects, _ = server.projects.get()
            target_project = next(
                (p for p in all_projects if p.name == project_name), None
            )

            if not target_project:
                available = [p.name for p in all_projects]
                raise ValueError(f"Project '{project_name}' not found. Available projects: {available}")

            logger.info(f"Found project '{project_name}' (ID: {target_project.id})")

            # Prepare the datasource
            datasource = TSC.DatasourceItem(target_project.id, name=datasource_name)

            logger.info(f"Publishing {file_path} as '{datasource_name}' (Mode: {mode})...")

            # Publish
            try:
                published_item = server.datasources.publish(
                    datasource,
                    file_path,
                    mode=publish_mode
                )
            except TSC.ServerResponseError as e:
                if e.code == "404004" and mode == "Append":
                    logger.warning(f"Datasource '{datasource_name}' not found for Append. Switching to Overwrite (Create)...")
                    published_item = server.datasources.publish(
                        datasource,
                        file_path,
                        mode=TSC.Server.PublishMode.Overwrite
                    )
                else:
                    raise

            logger.info(f"Successfully published datasource ID: {published_item.id}")
            return published_item.id
