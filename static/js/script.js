async function generateQuestions() {
    const text = document.getElementById("inputText").value;
    const outputDiv = document.getElementById("output");
    outputDiv.innerHTML = "Generating questions...";
  
    const response = await fetch("/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ input_text: text })
    });
  
    const data = await response.json();
  
    if (data["questions"] && data["questions"].length > 0) {
      outputDiv.innerHTML = "<h2>Generated Questions:</h2>";
  
      data["questions"].forEach((q, index) => {
        const question = q.question_statement || "No question";
        const answer = q.answer || "Not available";
        const options = q.options || [];
  
        outputDiv.innerHTML += `<div><strong>${index + 1}. ${question}</strong><br>`;
  
        options.forEach((opt) => {
          outputDiv.innerHTML += `&nbsp;&nbsp;&nbsp;• ${opt}<br>`;
        });
  
        outputDiv.innerHTML += `<br><em>Answer: ${answer}</em></div><hr>`;
      });
    } else {
      outputDiv.innerHTML = "No questions could be generated.";
    }
  }
  