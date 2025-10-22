<?php
header('Content-Type: application/json');

// Enable error reporting for debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

try {
    // Debug: Log what we received
    error_log("POST data: " . print_r($_POST, true));
    error_log("FILES data: " . print_r($_FILES, true));

    // --- 1. Create main uploads folder ---
    $baseDir = __DIR__ . '/uploads';
    if (!is_dir($baseDir)) {
        if (!mkdir($baseDir, 0777, true)) {
            throw new Exception("Failed to create uploads directory");
        }
    }

    // --- 2. Create timestamped folder for this incident ---
    $timestamp = date('Ymd_His');
    $folder = $baseDir . '/' . $timestamp;
    if (!is_dir($folder)) {
        if (!mkdir($folder, 0777, true)) {
            throw new Exception("Failed to create incident folder");
        }
    }

    // --- 3. Handle overall photos ---
    $photos = [];
    if (isset($_FILES['photos']) && is_array($_FILES['photos']['tmp_name'])) {
        error_log("Processing photos...");
        
        foreach ($_FILES['photos']['tmp_name'] as $i => $tmp) {
            if ($_FILES['photos']['error'][$i] === UPLOAD_ERR_OK && is_uploaded_file($tmp)) {
                $originalName = $_FILES['photos']['name'][$i];
                $ext = pathinfo($originalName, PATHINFO_EXTENSION);
                $newFilename = uniqid() . '.' . $ext;
                $target = $folder . '/' . $newFilename;
                
                error_log("Moving photo: $tmp to $target");
                
                if (move_uploaded_file($tmp, $target)) {
                    $photos[] = $newFilename;
                    error_log("Successfully moved photo: $newFilename");
                } else {
                    error_log("Failed to move photo: $originalName");
                    throw new Exception("Failed to move overall photo #$i");
                }
            } else {
                error_log("Photo upload error: " . $_FILES['photos']['error'][$i]);
            }
        }
    } else {
        error_log("No photos found in FILES data");
    }

    // --- 4. Handle video ---
    $video = null;
    if (isset($_FILES['video']) && $_FILES['video']['error'] === UPLOAD_ERR_OK) {
        $ext = pathinfo($_FILES['video']['name'], PATHINFO_EXTENSION);
        $target = $folder . '/' . uniqid() . '.' . $ext;
        if (move_uploaded_file($_FILES['video']['tmp_name'], $target)) {
            $video = basename($target);
        }
    }

    // --- 5. Handle car photos ---
    $cars = [];
    if (isset($_POST['cars']) && is_array($_POST['cars'])) {
        foreach ($_POST['cars'] as $i => $carData) {
            $car = [
                'style' => $carData['style'] ?? '',
                'color' => $carData['color'] ?? '',
                'license' => $carData['license'] ?? '',
                'instate' => isset($carData['instate']) && $carData['instate'] === 'true',
                'state' => $carData['state'] ?? '',
                'photo' => null
            ];

            // Handle car photo
            if (isset($_FILES['cars']['tmp_name'][$i]['photo']) && 
                $_FILES['cars']['error'][$i]['photo'] === UPLOAD_ERR_OK) {
                $ext = pathinfo($_FILES['cars']['name'][$i]['photo'], PATHINFO_EXTENSION);
                $target = $folder . '/' . uniqid() . '.' . $ext;
                if (move_uploaded_file($_FILES['cars']['tmp_name'][$i]['photo'], $target)) {
                    $car['photo'] = basename($target);
                }
            }

            $cars[] = $car;
        }
    }

    // --- 6. Problems ---
    $problems = json_decode($_POST['problems'] ?? '[]', true);

    // --- 7. Collect all other info ---
    $data = [
        'timestamp' => date('Y-m-d H:i:s'),
        'date' => $_POST['date'] ?? '',
        'arrival' => $_POST['arrival'] ?? '',
        'departure' => $_POST['departure'] ?? '',
        'people' => $_POST['people'] ?? '',
        'notes' => $_POST['notes'] ?? '',
        'problems' => $problems,
        'photos' => $photos,
        'video' => $video,
        'cars' => $cars,
        'folder' => $timestamp
    ];

    // --- 8. Save data as JSON ---
    file_put_contents($folder . '/data.json', json_encode($data, JSON_PRETTY_PRINT));

    error_log("Incident saved successfully with " . count($photos) . " photos");
    echo json_encode(['status' => 'success', 'message' => 'Uploaded ' . count($photos) . ' photos']);

} catch (Exception $e) {
    error_log("Error: " . $e->getMessage());
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}
?>