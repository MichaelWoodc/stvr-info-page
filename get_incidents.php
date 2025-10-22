<?php
header('Content-Type: application/json');

try {
    $baseDir = __DIR__ . '/uploads';
    $incidents = [];
    
    if (is_dir($baseDir)) {
        $folders = array_diff(scandir($baseDir), ['.', '..']);
        
        foreach ($folders as $folder) {
            $folderPath = $baseDir . '/' . $folder;
            $dataFile = $folderPath . '/data.json';
            
            if (is_dir($folderPath) && file_exists($dataFile)) {
                $data = json_decode(file_get_contents($dataFile), true);
                if ($data) {
                    $data['folder'] = $folder;
                    $incidents[] = $data;
                }
            }
        }
    }
    
    echo json_encode($incidents);
} catch (Exception $e) {
    echo json_encode(['error' => $e->getMessage()]);
}
?>