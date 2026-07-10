// RBAC on the Azure AI Search service (deployed only when deploySearch = true):
//   web app -> Search Index Data Contributor (push/query documents via search_sync + API)
//   web app -> Search Service Contributor    (create/update the con-records index)

@description('Azure AI Search service name.')
param searchServiceName string

@description('Principal ID of the web app system-assigned identity.')
param webAppPrincipalId string

var searchIndexDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
)
var searchServiceContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
)

resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchServiceName
}

resource webAppSearchIndexDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, webAppPrincipalId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: searchIndexDataContributorRoleId
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource webAppSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, webAppPrincipalId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: searchServiceContributorRoleId
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
