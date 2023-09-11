function toggleDropdown() {
    var dropdownOptions = document.getElementById("dropdownOptions");
    if (dropdownOptions.style.display === "block") {
        dropdownOptions.style.display = "none";
    } else {
        dropdownOptions.style.display = "block";
    }
}

// Add a click event listener to the document
document.addEventListener("click", function (event) {
    var dropdown = document.querySelector(".dropdown");
    if (!dropdown.contains(event.target)) {
        // Clicked outside the dropdown, so close it
        var dropdownOptions = document.getElementById("dropdownOptions");
        dropdownOptions.style.display = "none";
    }
});

// Get references to the image and file input elements
const companyLogo = document.getElementById('companyLogo');
const imageUpload = document.getElementById('imageUpload');

// Add an event listener to the file input
imageUpload.addEventListener('change', function() {
    const selectedFile = imageUpload.files[0];

    // Check if a file is selected
    if (selectedFile) {
        // Create a FileReader to read the selected file as a data URL
        const reader = new FileReader();

        reader.onload = function(event) {
            // Set the src attribute of the image to the data URL
            companyLogo.src = event.target.result;
        };

        // Read the selected file as a data URL
        reader.readAsDataURL(selectedFile);
    }
});