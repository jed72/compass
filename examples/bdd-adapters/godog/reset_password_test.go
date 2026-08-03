// Step definitions for godog.
//
// Only this file differs from the other three adapters. The spec, the extract
// command and the run command are the same four steps in another idiom.
package main

import (
	"context"
	"fmt"
	"testing"

	"github.com/cucumber/godog"
)

const tokenLifetimeHours = 24

type resetState struct {
	ageHours int
	changes  []string
	ok       bool
	errMsg   string
}

func (s *resetState) reset(*godog.Scenario) {
	s.ageHours, s.changes, s.ok, s.errMsg = 0, nil, false, ""
}

func (s *resetState) tokenIssuedHoursAgo(hours int) error {
	s.ageHours = hours
	return nil
}

func (s *resetState) setsNewPassword(password string) error {
	switch {
	case s.ageHours >= tokenLifetimeHours:
		s.ok, s.errMsg = false, "token expired"
	case len(password) < 8:
		s.ok, s.errMsg = false, "password too short"
	default:
		s.changes = append(s.changes, password)
		s.ok, s.errMsg = true, ""
	}
	return nil
}

func (s *resetState) resetSucceeds() error {
	if !s.ok {
		return fmt.Errorf("expected the reset to succeed, got %q", s.errMsg)
	}
	return nil
}

func (s *resetState) resetRefusedWith(reason string) error {
	if s.ok {
		return fmt.Errorf("expected the reset to be refused")
	}
	if s.errMsg != reason {
		return fmt.Errorf("expected %q, got %q", reason, s.errMsg)
	}
	return nil
}

func (s *resetState) changeRecorded() error {
	if len(s.changes) != 1 {
		return fmt.Errorf("expected 1 recorded change, got %d", len(s.changes))
	}
	return nil
}

func (s *resetState) noChangeRecorded() error {
	if len(s.changes) != 0 {
		return fmt.Errorf("expected no recorded change, got %d", len(s.changes))
	}
	return nil
}

func InitializeScenario(ctx *godog.ScenarioContext) {
	s := &resetState{}
	ctx.Before(func(c context.Context, sc *godog.Scenario) (context.Context, error) {
		s.reset(sc)
		return c, nil
	})
	ctx.Step(`^a password reset token issued (\d+) hours ago$`, s.tokenIssuedHoursAgo)
	ctx.Step(`^the user sets the new password "([^"]*)"$`, s.setsNewPassword)
	ctx.Step(`^the reset succeeds$`, s.resetSucceeds)
	ctx.Step(`^the reset is refused with "([^"]*)"$`, s.resetRefusedWith)
	ctx.Step(`^the password change is recorded$`, s.changeRecorded)
	ctx.Step(`^no password change is recorded$`, s.noChangeRecorded)
}

func TestFeatures(t *testing.T) {
	suite := godog.TestSuite{
		ScenarioInitializer: InitializeScenario,
		Options: &godog.Options{
			Format:   "pretty",
			Paths:    []string{"features"},
			TestingT: t,
		},
	}
	if suite.Run() != 0 {
		t.Fatal("non-zero status returned, failed to run feature tests")
	}
}
