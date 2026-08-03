// Step definitions for cucumber-js.
//
// Only this file differs from the other three adapters. The spec, the extract
// command and the run command are the same four steps in another idiom.
import { Given, When, Then, Before } from '@cucumber/cucumber';
import assert from 'node:assert';

const TOKEN_LIFETIME_HOURS = 24;

Before(function () {
  this.changes = [];
});

Given('a password reset token issued {int} hours ago', function (hours) {
  this.ageHours = hours;
});

When('the user sets the new password {string}', function (password) {
  if (this.ageHours >= TOKEN_LIFETIME_HOURS) {
    this.result = { ok: false, error: 'token expired' };
  } else if (password.length < 8) {
    this.result = { ok: false, error: 'password too short' };
  } else {
    this.changes.push(password);
    this.result = { ok: true, error: null };
  }
});

Then('the reset succeeds', function () {
  assert.ok(this.result.ok, this.result.error);
});

Then('the reset is refused with {string}', function (reason) {
  assert.ok(!this.result.ok, 'expected the reset to be refused');
  assert.strictEqual(this.result.error, reason);
});

Then('the password change is recorded', function () {
  assert.strictEqual(this.changes.length, 1);
});

Then('no password change is recorded', function () {
  assert.deepStrictEqual(this.changes, []);
});
