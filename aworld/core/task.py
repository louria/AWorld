# coding: utf-8
# Copyright (c) 2025 inclusionAI.
import abc
import uuid
from dataclasses import dataclass, field
from typing import Any, Union, List, Dict, Callable, Optional

from pydantic import BaseModel

from aworld.agents.llm_agent import Agent
from aworld.core.agent.swarm import Swarm
from aworld.core.common import Config
from aworld.core.context.base import Context
from aworld.core.tool.base import Tool, AsyncTool
from aworld.output.outputs import Outputs, DefaultOutputs


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid1().hex)
    name: str = field(default_factory=lambda: uuid.uuid1().hex)
    user_id: str = field(default=None)
    session_id: str = field(default=None)
    input: Any = field(default=None)
    # task config
    conf: Config = field(default=None)
    # global tool instance
    tools: List[Union[Tool, AsyncTool]] = field(default_factory=list)
    # global tool names
    tool_names: List[str] = field(default_factory=list)
    # custom tool conf
    tools_conf: Config = field(default_factory=dict)
    # custom mcp servers conf
    mcp_servers_conf: Config = field(default_factory=dict)
    swarm: Optional[Swarm] = field(default=None)
    agent: Optional[Agent] = field(default=None)
    event_driven: bool = field(default=True)
    # for loop detect
    endless_threshold: int = field(default=3)
    # task_outputs
    outputs: Outputs = field(default_factory=DefaultOutputs)
    # task special runner class, for example: package.XXRunner
    runner_cls: Optional[str] = field(default=None)
    # such as: {"start": ["init_tool", "init_context", ...]}
    hooks: Dict[str, List[str]] = field(default_factory=dict)
    # task specified context
    context: 'Context' = field(default=None)
    is_sub_task: bool = field(default=False)
    group_id: str = field(default=None)
    max_retry_count: int = 0


@dataclass
class TaskResponse:
    id: str = field(default=None)
    answer: str | None = field(default=None)
    context: Context | None = field(default_factory=Context)
    usage: Dict[str, Any] | None = field(default_factory=dict)
    time_cost: float | None = field(default=0.0)
    success: bool = field(default=False)
    msg: str | None = field(default=None)
    trajectory: List[Dict[str, Any]] = field(default_factory=list)


class Runner(object):
    __metaclass__ = abc.ABCMeta

    _use_demon: bool = False
    daemon_target: Callable[..., Any] = None
    context: Context = None

    async def pre_run(self):
        pass

    async def post_run(self):
        pass

    @abc.abstractmethod
    async def do_run(self, context: Context = None):
        """Raise exception if not success."""

    async def _daemon_run(self):
        if self._use_demon and self.daemon_target and callable(self.daemon_target):
            import threading
            t = threading.Thread(target=self.daemon_target, name="daemon", daemon=True)
            t.start()

    async def run(self) -> Any:
        try:
            await self.pre_run()
            await self._daemon_run()
            ret = await self.do_run(self.context)
            if ret is None:
                ret = TaskResponse(id=self.context.task_id if self.context else "", success=False, msg = "Task return None.")
            return ret
        except BaseException as ex:
            self._exception = ex
            # do record or report
            raise ex
        finally:
            await self.post_run()
