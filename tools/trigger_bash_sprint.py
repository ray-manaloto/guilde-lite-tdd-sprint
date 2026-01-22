import asyncio
import logging
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

from app.db.session import async_session_maker
from app.services.spec import SpecService
from app.schemas.spec import SpecCreate, SpecPlanningAnswer
from app.services.sprint import SprintService
from app.schemas.sprint import SprintCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bash_sprint")

async def run_bash_sprint():
    async with async_session_maker() as session:
        spec_service = SpecService(session)
        sprint_service = SprintService(session)

        task = "Generate a BASH SHELL SCRIPT (hello.sh) that prints hello world. Do NOT use Python."
        logger.info(f"--- Starting Interview for: '{task}' ---")
        
        spec_in = SpecCreate(title="Bash Hello World", task=task)
        spec, planning = await spec_service.create_with_planning(spec_in, max_questions=2)
        
        questions = planning['questions']
        answers = []
        for q in questions:
            ans_text = "Use Bash. Create a file named hello.sh. Make it executable."
            answers.append(SpecPlanningAnswer(question=q['question'], answer=ans_text))

        await spec_service.save_planning_answers(spec.id, answers)
        await session.commit()

        sprint_in = SprintCreate(name="bash002", goal=task, spec_id=spec.id)
        sprint = await sprint_service.create(sprint_in)
        await session.commit()
        
        logger.info(f"Sprint Created: {sprint.id}")
        logger.info("Build pipeline triggered.")

if __name__ == "__main__":
    asyncio.run(run_bash_sprint())
