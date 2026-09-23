from typing import Annotated
import strawberry
from strawberry.extensions import MaxAliasesLimiter, QueryDepthLimiter
from fastapi import Depends
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from app.core.security import Principal, current_principal
from app.api.v1.routes import operations


async def context(principal: Annotated[Principal, Depends(current_principal)]):
    return {'principal': principal}


@strawberry.type
class GraphDashboard:
    protected_assets: int
    active_alerts: int
    risk_score: int
    event_rate: int


@strawberry.type
class Query:
    @strawberry.field
    async def dashboard(self, info: Info) -> GraphDashboard:
        overview = await operations().overview(info.context['principal'])
        return GraphDashboard(protected_assets=overview.protected_assets, active_alerts=overview.active_alerts, risk_score=overview.risk_score, event_rate=overview.event_rate)


schema = strawberry.Schema(query=Query, extensions=[lambda: MaxAliasesLimiter(max_alias_count=5), lambda: QueryDepthLimiter(max_depth=4)])
graphql_router = GraphQLRouter(schema, graphql_ide=None, context_getter=context)
