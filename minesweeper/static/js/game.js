document.addEventListener("DOMContentLoaded", () => {
    const startGameBtn = document.getElementById("startGame");
    const gameBoard = document.getElementById("gameBoard");
    const moneyDisplay = document.getElementById("money");
    const betAmountInput = document.getElementById("betAmount");
    const numMinesInput = document.getElementById("numMines");

    const submitSelection = document.createElement("button");
    submitSelection.textContent = "Submit";
    submitSelection.style.display = "none";
    submitSelection.id = "submit-btn";
    document.body.appendChild(submitSelection);

    let selectedCells = [];
    let boardData = [];
    let gameOver = false;

    // Function to restart the game after a delay
    function restartGame() {
        setTimeout(() => {
            startGameBtn.click(); // Simulate button click to start a new game
        }, 3000); // Restart after 3 seconds
    }

    // Start game
    startGameBtn.addEventListener("click", () => {
        if (gameOver) return;

        const betAmount = parseInt(betAmountInput.value);
        const numMines = parseInt(numMinesInput.value);

        if (isNaN(betAmount) || isNaN(numMines) || betAmount <= 0 || numMines <= 0) {
            alert("Enter valid values for bet amount and number of mines.");
            return;
        }

        fetch("/start_game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bet_amount: betAmount, num_mines: numMines })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            moneyDisplay.textContent = data.money;
            boardData = data.board;
            selectedCells = [];
            gameOver = false;
            submitSelection.style.display = "none";
            createBoard(boardData);
        })
        .catch(err => console.error("Error starting game:", err));
    });

    // Create the game board
    function createBoard(board, revealMines = false) {
        gameBoard.innerHTML = "";
        board.forEach((row, rowIndex) => {
            row.forEach((cell, colIndex) => {
                const cellElement = document.createElement("div");
                cellElement.classList.add("cell");
                cellElement.dataset.row = rowIndex;
                cellElement.dataset.col = colIndex;

                if (cell === "clicked") {
                    cellElement.classList.add("safe");
                    cellElement.textContent = "✔";
                    cellElement.style.backgroundColor = "green"; // Highlight safe cells
                } else if (cell === "mine" && revealMines) {
                    cellElement.classList.add("mine");
                    cellElement.textContent = "💣";
                }

                cellElement.addEventListener("click", () => handleCellClick(rowIndex, colIndex, cellElement));
                gameBoard.appendChild(cellElement);
            });
        });
    }

    // Handle cell click
    function handleCellClick(row, col, cellElement) {
        if (gameOver || selectedCells.some(([r, c]) => r === row && c === col)) return;

        fetch("/click_cell", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row, col })
        })
        .then(response => response.json())
        .then(data => {
            if (data.result === "mine") {
                cellElement.classList.add("mine");
                cellElement.textContent = "💣";
                alert("Game Over! You hit a mine.");
                gameOver = true;
                revealMines(); // Show all mines immediately
                restartGame(); // Restart after game over
            } else {
                selectedCells.push([row, col]);
                cellElement.classList.add("safe");
                cellElement.textContent = "✔";
                cellElement.style.backgroundColor = "green"; // Safe cells turn green
                submitSelection.style.display = "block"; // Show submit button
            }
        })
        .catch(err => console.error("Error selecting cell:", err));
    }

    // Submit selected cells
    submitSelection.addEventListener("click", () => {
        if (gameOver) return;

        fetch("/submit_selection", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ selected_cells: selectedCells })
        })
        .then(response => response.json())
        .then(data => {
            if (data.result === "lost") {
                alert("Game Over! You hit a mine.");
                createBoard(data.revealed_board, true);
                gameOver = true;
                restartGame(); // Restart after game over
            } else {
                alert(`Congratulations! You won $${data.money}`);
                createBoard(data.board);
            }
            moneyDisplay.textContent = data.new_balance; // Update scoreboard
            selectedCells = [];
            submitSelection.style.display = "none";
            restartGame(); // Restart after winning
        })
        .catch(err => console.error("Error submitting selection:", err));
    });

    // Reveal all mines when the game is lost
    function revealMines() {
        document.querySelectorAll(".cell").forEach(cell => {
            const row = cell.dataset.row;
            const col = cell.dataset.col;
            if (boardData[row][col] === "mine") {
                cell.classList.add("mine");
                cell.textContent = "💣";
            }
        });
    }
});
