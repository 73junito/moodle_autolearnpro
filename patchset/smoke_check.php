<?php
// Minimal smoke check: bootstrap Moodle and inspect assign file submission options.
define('CLI_SCRIPT', true);
require '/var/www/html/moodle/config.php';
// Ensure assign plugin base classes are loaded first.
require_once($CFG->dirroot . '/mod/assign/locallib.php');
require_once($CFG->dirroot . '/mod/assign/submission/file/locallib.php');

try {
    // Create minimal objects to instantiate the plugin. These may be incomplete,
    // but we'll try to call the private method via reflection to inspect options.
    // Create minimal course and assign objects.
    $course = new stdClass();
    $course->id = 1;
    $cm = null;
    $context = context_system::instance();
    $assignobj = new assign($context, $cm, $course);

    // Instantiate plugin (type name 'file').
    $plugin = new assign_submission_file($assignobj, 'file');

    $rm = new ReflectionMethod($plugin, 'get_file_options');
    $rm->setAccessible(true);
    $options = $rm->invoke($plugin);

    echo "get_file_options() returned:\n";
    var_export($options);
    echo "\n\naccepted_types: ";
    if (isset($options['accepted_types'])) {
        var_export($options['accepted_types']);
    } else {
        echo "<missing>\n";
    }
} catch (Throwable $e) {
    echo "ERROR: ", $e->getMessage(), "\n";
    echo $e->getTraceAsString(), "\n";
}

// Expanded checks: simulate assign plugin save without web-only add_moduleinfo().
$runexpanded = false;
if (isset($argv) && is_array($argv)) {
    foreach ($argv as $a) {
        if ($a === '--run-expanded') {
            $runexpanded = true;
        }
    }
}
if ($runexpanded) {
    try {
        echo "Running expanded smoke-checks (simulation)...\n";

        // Use admin user context for operations (avoid session DB writes).
        $admin = get_admin();
        global $USER; $USER = $admin;

        // Ensure minimal libs available.
        require_once($CFG->dirroot . '/course/lib.php');

        // 1) Create a draft item and write a test file (tests filemanager/draft handling).
        $fs = get_file_storage();
        $draftitemid = file_get_unused_draft_itemid();
        // Use system context for draft creation if module context not available yet.
        $context = context_system::instance();
        $filecontent = "Hello, smoke test file";
        $file_record = array(
            'contextid' => $context->id,
            'component' => 'user',
            'filearea' => 'draft',
            'itemid' => $draftitemid,
            'filepath' => '/',
            'filename' => 'smoke.txt'
        );
        $fs->create_file_from_string($file_record, $filecontent);
        echo "Wrote draft file, draftid={$draftitemid}\n";

        // 1b) Verify file_storage record for the draft item.
        $files = $fs->get_area_files($context->id, 'user', 'draft', $draftitemid);
        $stored = array();
        foreach ($files as $f) {
            if ($f->is_directory()) { continue; }
            $stored[] = $f;
        }
        $cnt = count($stored);
        if ($cnt !== 1) {
            echo "FAIL: expected 1 stored file in draft area, found {$cnt}\n";
        } else {
            $sf = $stored[0];
            $fname = $sf->get_filename();
            $fsize = $sf->get_filesize();
            $fmime = $sf->get_mimetype();
            $fcontent = $sf->get_content();
            $ok = true;
            if ($fname !== 'smoke.txt') { $ok = false; echo "FAIL: filename mismatch ({$fname})\n"; }
            $expected = strlen($filecontent);
            if ((int)$fsize !== (int)$expected) {
                $ok = false;
                echo "FAIL: filesize mismatch ({$fsize} != {$expected})\n";
            }
            if ($fcontent !== $filecontent) { $ok = false; echo "FAIL: file content mismatch\n"; }
            if ($ok) { echo "PASS: draft file verified (name={$fname}, size={$fsize}, mime={$fmime})\n"; }
        }

        // 2) Try to locate an existing assign instance to exercise the plugin save path.
        global $DB;
        $assigninstance = $DB->get_record_sql('SELECT * FROM {assign} LIMIT 1', null, IGNORE_MISSING);
        if ($assigninstance) {
            echo "Found assign instance id={$assigninstance->id}, attempting plugin save...\n";
            $cm = get_coursemodule_from_instance('assign', $assigninstance->id, 0, false, IGNORE_MISSING);
            if ($cm) {
                $course = get_course($cm->course);
                $assign = new assign(context_module::instance($cm->id), $cm, $course);

                // Create a minimal submission record for admin.
                $subrec = new stdClass();
                $subrec->assignment = $assign->get_instance()->id;
                $subrec->userid = $admin->id;
                $subrec->attemptnumber = 0;
                $subrec->status = ASSIGN_SUBMISSION_STATUS_DRAFT;
                $subrec->timecreated = time();
                $subrec->timemodified = time();
                $submissionid = $DB->insert_record('assign_submission', $subrec);
                echo "Created submission id={$submissionid}\n";

                $submission = $DB->get_record('assign_submission', array('id' => $submissionid));
                $filesub = $assign->get_submission_plugin_by_type('file');
                if ($filesub) {
                    $data = new stdClass();
                    $data->filemanager = $draftitemid;
                    $data->files = $draftitemid;
                    $saved = $filesub->save($submission, $data);
                    echo "assign_submission_file->save() returned: "; var_export($saved); echo "\n";
                } else {
                    echo "No file submission plugin found for this assign instance.\n";
                }
            } else {
                echo "Assign instance found but course module not available; skipping plugin save.\n";
            }
        } else {
            echo "No assign instances found; skipping plugin save and verifying draft storage only.\n";
        }

        // 3) Messaging test: send a simple message from admin to admin.
        $msgdata = array(
            'component' => 'local_smoketests',
            'name' => 'smoke',
            'userfrom' => core_user::get_noreply_user(),
            'userto' => $admin,
            'subject' => 'Smoke test message',
            'fullmessage' => 'This is a smoke test message.',
            'fullmessageformat' => FORMAT_HTML,
            'fullmessagehtml' => '<p>This is a smoke test message.</p>',
            'smallmessage' => 'smoke'
        );
        $eventdata = new \core\message\message($msgdata);
        message_send($eventdata);
        echo "Sent test message to admin.\n";

    } catch (Throwable $e) {
        echo "EXC: ".$e->getMessage()."\n";
        echo $e->getTraceAsString();
    }
}
