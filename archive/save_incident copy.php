<?php
header('Content-Type: application/json');

$upload_root = "uploads/";
if (!file_exists($upload_root)) mkdir($upload_root, 0777, true);

// Create unique folder for this incident
$folder_name = date("Ymd_His");
$incident_dir = $upload_root . $folder_name . "/";
mkdir($incident_dir, 0777, true);

// Save uploads
$photoFiles = [];
if (!empty($_FILES['photos']['name'][0])) {
  foreach ($_FILES['photos']['tmp_name'] as $key => $tmp_name) {
    $safe_name = time() . "_" . basename($_FILES['photos']['name'][$key]);
    move_uploaded_file($tmp_name, $incident_dir . $safe_name);
    $photoFiles[] = $safe_name;
  }
}

$videoFile = null;
if (!empty($_FILES['video']['name'])) {
  $safe_video = time() . "_" . basename($_FILES['video']['name']);
  move_uploaded_file($_FILES['video']['tmp_name'], $incident_dir . $safe_video);
  $videoFile = $safe_video;
}

// Collect data
$data = [
  "timestamp" => date("Y-m-d H:i:s"),
  "date" => $_POST['date'] ?? "",
  "arrival" => $_POST['arrival'] ?? "",
  "departure" => $_POST['departure'] ?? "",
  "people" => $_POST['people'] ?? "",
  "notes" => $_POST['notes'] ?? "",
  "problems" => json_decode($_POST['problems'] ?? "[]", true),
  "cars" => json_decode($_POST['cars'] ?? "[]", true),
  "photos" => $photoFiles,
  "video" => $videoFile
];

// Save metadata JSON
file_put_contents($incident_dir . "meta.json", json_encode($data, JSON_PRETTY_PRINT));

echo json_encode(["success" => true, "folder" => $folder_name]);
