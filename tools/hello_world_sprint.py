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
logger = logging.getLogger("hello_world_sprint")

async def run_hello_world():
    async with async_session_maker() as session:
        spec_service = SpecService(session)
        sprint_service = SprintService(session)

        # 1. Start Interview
        task = "Build a python script to print hello world"
        logger.info(f"--- 1. Starting Interview for: '{task}' ---")
        
        spec_in = SpecCreate(title="Hello World Script", task=task)
        # Trigger the backend to generate questions
        spec, planning = await spec_service.create_with_planning(spec_in, max_questions=2)
        
        questions = planning['questions']
        logger.info(f"System generated {len(questions)} questions:")
        
        # 2. Populate the Questionnaire (Simulating the User)
        answers = []
        for q in questions:
            q_text = q['question']
            logger.info(f"  Q: {q_text}")
            
            # Simple logic to provide relevant answers
            ans_text = "Use Python 3. No external libraries needed. Just print 'Hello World' to standard output."
            
            logger.info(f"  A: {ans_text}")
            answers.append(SpecPlanningAnswer(question=q_text, answer=ans_text))

        # 3. Save Answers
        await spec_service.save_planning_answers(spec.id, answers)
        await session.commit()
        logger.info("--- 2. Interview Completed & Answers Saved ---")

        # 4. Create Sprint (Triggers the Build)
        sprint_in = SprintCreate(name="Hello World Sprint", goal=task, spec_id=spec.id)
        sprint = await sprint_service.create(sprint_in)
        await session.commit()
        
        logger.info(f"--- 3. Sprint Created: {sprint.id} ---")
        logger.info(f"Status: {sprint.status}")
        logger.info("Build pipeline (PhaseRunner) has been triggered in the background.")

if __name__ == "__main__":
    asyncio.run(run_hello_world())
