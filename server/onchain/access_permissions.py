from entities import AccessPermissionsResponse, PersonalServerRequest


class AccessPermissions:
    def fetch_access_permissions(
        self, app_address: str, request: PersonalServerRequest
    ) -> AccessPermissionsResponse:
        # TODO Should this be fetched from the subgraph or the contract?
        return AccessPermissionsResponse(
            app_address, request.file_ids, request.operation, request.parameters
        )
