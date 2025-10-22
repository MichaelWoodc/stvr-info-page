<?php
header('Content-Type: application/json');

$upload_root = "uploads/";
$folders = array_filter(glob($upload_root . "*"), 'is_dir');

// Sort by folder name descending (newest first)
rsort($folders);

$incidents = [];
foreach ($folders as $folder) {
  $metaFile = $folder . "/meta.json";
  if (file_exists($metaFile)) {
    $json = json_decode(file_get_contents($metaFile), true);
    $json["folder"] = basename($folder);
    $incidents[] = $json;
  }
}

echo json_encode($incidents);
