const handleQuestionnaireSubmit = async (answers: UserAnswer[]) => {
    const customAnswers = answers.filter(answer => answer.custom_answer !== '');
    let results: PartyResult[] | null = null;

    if (customAnswers.length > 0) {
        console.log("customAnswers", customAnswers);
        try {
            const response = await fetch(`${__API_URL__}/custom_answer_evaluation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    custom_answers: customAnswers,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const evaluationResults: PartyResult[] = await response.json();
            setSavedAnswers(answers);
            setResult(evaluationResults);
            setEvaluationMode(false);
            console.log("EVAL:", JSON.stringify(evaluationResults));
        } catch (error) {
            console.error('Error sending custom answers:', error);
        }
    } else {
        // Local scoring
        results = calculateResults(answers, questionsData);
        console.log("RESULTS frontend: ", JSON.stringify(results, null, 2));
        setSavedAnswers(answers);
        setResult(results);
        setEvaluationMode(false);
    }
}; 