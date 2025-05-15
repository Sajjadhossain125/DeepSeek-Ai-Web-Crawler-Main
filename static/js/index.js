document.addEventListener("DOMContentLoaded", function () {
  const status = document.getElementById("status");
  const startBtn = document.getElementById("startBtn");
  const downloadBtn = document.getElementById("downloadBtn");
  const logContainer = document.getElementById("log");
  let table = null;
  const maxPages = parseInt($('#maxPages').val());

  const eventSource = new EventSource("/log-stream");

  eventSource.onmessage = function (event) {
    const logLine = document.createElement("div");
    logLine.textContent = event.data;
    logContainer.appendChild(logLine);
    logContainer.scrollTop = logContainer.scrollHeight;
  };

  startBtn.addEventListener("click", () => {
    const baseUrl = document.getElementById("baseUrl").value.trim();
    const cssSelector = document.getElementById("cssSelector").value.trim();
    const requiredKeysInput = document.getElementById("requiredKeys").value.trim();

    if (!baseUrl || !cssSelector || !requiredKeysInput) {
      alert("Please fill all fields (URL, selector, required keys).");
      return;
    }

    const requiredKeys = requiredKeysInput.split(",").map(k => k.trim());

    status.textContent = "Scraping in progress...";
    startBtn.disabled = true;
    logContainer.innerHTML = "";

    fetch("/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_url: baseUrl, css_selector: cssSelector, required_keys: requiredKeys, max_pages: maxPages }),
    })
      .then((res) => res.json())
      .then((data) => {
        // Destroy existing DataTable if exists
        if (table) {
          table.destroy();
        }

        // Build new headers dynamically
        const tableElement = document.getElementById("venuesTable");
        tableElement.innerHTML = ""; // Clear previous table content

        const thead = document.createElement("thead");
        const headRow = document.createElement("tr");
        requiredKeys.forEach((key) => {
          const th = document.createElement("th");
          th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
          headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        tableElement.appendChild(thead);

        const tbody = document.createElement("tbody");
        data.forEach((venue) => {
          const row = document.createElement("tr");
          requiredKeys.forEach((key) => {
            const td = document.createElement("td");
            td.textContent = venue[key] ?? ""; // fallback if key is missing
            row.appendChild(td);
          });
          tbody.appendChild(row);
        });
        tableElement.appendChild(tbody);

        // Reinitialize DataTable
        table = $("#venuesTable").DataTable();

        status.textContent = `Scraping complete. ${data.length} venues found.`;
        downloadBtn.disabled = false;
        startBtn.disabled = false;
      })
      .catch((err) => {
        console.error(err);
        status.textContent = "Error during scraping.";
        startBtn.disabled = false;
      });
  });

  downloadBtn.addEventListener("click", () => {
    window.location.href = "/download";
  });
});
