import strawberry
from strawberry.fastapi import GraphQLRouter

from app.services.intelligence import intelligence_service


@strawberry.type
class GraphDashboard:
    protected_assets: int
    active_alerts: int
    risk_score: int
    event_rate: int


@strawberry.type
class Query:
    @strawberry.field
    def dashboard(self) -> GraphDashboard:
        overview = intelligence_service.overview("demo-tenant")
        return GraphDashboard(
            protected_assets=overview.protected_assets,
            active_alerts=overview.active_alerts,
            risk_score=overview.risk_score,
            event_rate=overview.event_rate,
        )


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema, graphql_ide=None)

